package mg.admvalue.core.recruitment.services;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import mg.admvalue.core.common.exceptions.ElementNotFoundException;
import mg.admvalue.core.common.exceptions.FormValidationException;
import mg.admvalue.core.common.exceptions.MessageException;
import mg.admvalue.core.recruitment.database.mongo.documents.RecruitmentExecutionDocument;
import mg.admvalue.core.recruitment.database.mongo.documents.StepHistoryEntryDocument;
import mg.admvalue.core.recruitment.database.mongo.repositories.RecruitmentExecutionRepository;
import mg.admvalue.core.recruitment.database.postgres.entities.CandidateEntity;
import mg.admvalue.core.recruitment.database.postgres.entities.ProcessEntity;
import mg.admvalue.core.recruitment.database.postgres.entities.StepEntity;
import mg.admvalue.core.recruitment.database.postgres.repositories.CandidateInfoRepository;
import mg.admvalue.core.recruitment.database.postgres.repositories.IRecruitmentBlacklistRepository;
import mg.admvalue.core.recruitment.database.postgres.repositories.RecruitmentProcessRepository;
import mg.admvalue.core.recruitment.dtos.*;
import mg.admvalue.core.recruitment.enums.ExecutionStatus;
import mg.admvalue.core.recruitment.enums.FinalResult;
import mg.admvalue.core.recruitment.enums.StepDecision;
import mg.admvalue.core.recruitment.mappers.RecruitmentExecutionMapper;
import mg.admvalue.core.recruitment.mappers.StepHistoryMapper;
import mg.admvalue.core.user.domain.ports.inbound.AuthenticationUseCase;
import org.jspecify.annotations.NonNull;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@RequiredArgsConstructor
@Service
public class RecruitmentExecutionCommandServiceImpl implements RecruitmentExecutionCommandService {

    private final RecruitmentExecutionRepository executionRepository;

    private final RecruitmentProcessRepository processQueryRepository;

    private final CandidateInfoRepository candidateRepository;

    // Renommé : checBlacklist -> blacklistRepository (comment #4)
    private final IRecruitmentBlacklistRepository blacklistRepository;

    private final RecruitmentExecutionStepResolver stepResolver;

    // Doublon supprimé : mapper et executionMapper étaient le même bean (comment #2)
    private final RecruitmentExecutionMapper executionMapper;

    private final AuthenticationUseCase authenticationUseCase;

    private final StepHistoryMapper stepHistoryMapper;

    @Override
    @Transactional
    public RecruitmentExecutionResponseDTO start(StartExecutionRequestDTO request)
        throws ElementNotFoundException, MessageException, FormValidationException {

        CandidateEntity candidate = candidateRepository
            .findById(request.getCandidateId())
            .orElseThrow(() -> new ElementNotFoundException("Candidat introuvable avec l'id : " + request.getCandidateId()));

        ProcessEntity process = findProcessOrThrow(request.getProcessId().toString());
        return executionMapper.toDTO(bulk(process, List.of(candidate)).get(0));
    }

    @Override
    @Transactional
    public RecruitmentExecutionResponseDTO recordDecision(String executionId, StepDecisionRequestDTO request)
        throws ElementNotFoundException, FormValidationException {

        RecruitmentExecutionDocument execution = findExecutionOrThrow(executionId);
        validateInProgress(execution);

        ProcessEntity process = findProcessOrThrow(execution.getProcessId());
        Integer currentRank = execution.getCurrentRank();
        List<StepEntity> stepsAtRank = stepResolver.resolveActiveStepsAtRank(process, currentRank);

        StepEntity targetStep = resolveTargetStep(stepsAtRank, request.getStepCode());
        ensureNotAlreadyDecided(execution, currentRank, targetStep.getCode(),
            "stepCode", "Cette étape a déjà été décidée pour ce candidat");

        String evaluatedBy = authenticationUseCase.getCurrentUsername();
        LocalDateTime now = LocalDateTime.now();

        execution.getStepsHistory().add(
            stepHistoryMapper.toEntry(targetStep, request.getResult(), request.getComment(), evaluatedBy, now)
        );
        execution.setUpdatedAt(now);

        if (request.getResult() == StepDecision.ABSENT) {
            applyAbsenceCascade(execution, stepsAtRank, targetStep, evaluatedBy, now);
            closeExecution(execution, FinalResult.NO_SHOW, request.getComment());
            return executionMapper.toDTO(executionRepository.save(execution));
        }
        if (request.getResult() == StepDecision.KO && stepsAtRank.size() == 1) {
            applyDinedCascade(execution, stepsAtRank, targetStep, evaluatedBy, now);
            closeExecution(execution, FinalResult.NO_SHOW, request.getComment());
            return executionMapper.toDTO(executionRepository.save(execution));
        }

        advanceRankIfComplete(execution, process, currentRank, stepsAtRank);
        return executionMapper.toDTO(executionRepository.save(execution));
    }

    @Override
    @Transactional
    public RecruitmentExecutionResponseDTO recordBlockDecision(String executionId, BlockDecisionRequestDTO request)
        throws ElementNotFoundException, FormValidationException {

        RecruitmentExecutionDocument execution = findExecutionOrThrow(executionId);
        StepDecision result = StepDecision.valueOf(request.getResult());

        validateAwaitingBlockDecision(execution);

        ProcessEntity process = findProcessOrThrow(execution.getProcessId());
        Integer currentRank = execution.getCurrentRank();
        List<StepEntity> stepsAtRank = stepResolver.resolveActiveStepsAtRank(process, currentRank);

        validateMultiStepRank(stepsAtRank);

        String blockCode = "RANK_" + currentRank + "_DECISION";
        ensureNotAlreadyDecided(execution, currentRank, blockCode,
            "rank", "La décision finale de ce bloc a déjà été enregistrée");

        if (!isRankComplete(execution, currentRank, stepsAtRank)) {
            FormValidationException ex = new FormValidationException();
            ex.reject("rank", "Toutes les sous-étapes doivent être décidées individuellement avant de pouvoir prendre la décision finale.");
            throw ex;
        }

        String blockTitle = stepsAtRank.stream().map(StepEntity::getName).collect(Collectors.joining(" + "));
        String evaluatedBy = authenticationUseCase.getCurrentUsername();
        LocalDateTime now = LocalDateTime.now();
        StepHistoryEntryDocument blockEntry = stepHistoryMapper.toBlockEntry(
            blockCode, blockTitle, currentRank, result, request.getComment(), evaluatedBy, now
        );
        execution.getStepsHistory().add(blockEntry);
        execution.setUpdatedAt(now);

        if (result == StepDecision.KO) {
            closeExecution(execution, FinalResult.NO_SHOW, request.getComment());
        } else {
            Optional<Integer> nextRank = stepResolver.resolveNextActiveRank(process, currentRank);
            execution.setCurrentRank(nextRank.orElse(null));
        }

        return executionMapper.toDTO(executionRepository.save(execution));
    }

    @Override
    @Transactional
    public RecruitmentExecutionResponseDTO recordFinalDecision(String executionId, FinalDecisionRequestDTO request)
        throws ElementNotFoundException, FormValidationException {

        RecruitmentExecutionDocument execution = findExecutionOrThrow(executionId);
        validateAwaitingFinalDecision(execution);

        closeExecution(execution, request.getFinalResult(), request.getReason());

        return executionMapper.toDTO(executionRepository.save(execution));
    }

    private void closeExecution(RecruitmentExecutionDocument execution, FinalResult finalResult, String reason) {
        execution.setStatus(ExecutionStatus.COMPLETED);
        execution.setCurrentRank(null);
        execution.setFinalResult(finalResult);
        execution.setFinalResultReason(reason);
    }

    private Set<String> resolveDecidedStepCodes(RecruitmentExecutionDocument execution, Integer rank) {
        return execution.getStepsHistory().stream()
            .filter(entry -> rank.equals(entry.getStepRankAtExecution()))
            .map(StepHistoryEntryDocument::getStepCode)
            .collect(Collectors.toSet());
    }

    private boolean isRankComplete(RecruitmentExecutionDocument execution, Integer rank, List<StepEntity> stepsAtRank) {
        Set<String> requiredCodes = stepsAtRank.stream().map(StepEntity::getCode).collect(Collectors.toSet());
        Set<String> decidedCodes = resolveDecidedStepCodes(execution, rank);
        return decidedCodes.containsAll(requiredCodes);
    }

    private RecruitmentExecutionDocument findExecutionOrThrow(String executionId) throws ElementNotFoundException {
        return executionRepository.findById(executionId)
            .orElseThrow(() -> new ElementNotFoundException(
                "Exécution de recrutement introuvable avec l'id : " + executionId));
    }

    private ProcessEntity findProcessOrThrow(String processId) throws ElementNotFoundException {
        return processQueryRepository.findById(UUID.fromString(processId))
            .orElseThrow(() -> new ElementNotFoundException(
                "Process de recrutement introuvable avec l'id : " + processId));
    }

    private StepEntity resolveTargetStep(List<StepEntity> stepsAtRank, String stepCode) throws FormValidationException {
        return stepsAtRank.stream()
            .filter(step -> stepCode.equals(step.getCode()))
            .findFirst()
            .orElseThrow(() -> {
                FormValidationException ex = new FormValidationException();
                ex.reject("stepCode", "Aucune étape active avec ce code au rang courant du candidat");
                return ex;
            });
    }

    private void ensureNotAlreadyDecided(RecruitmentExecutionDocument execution, Integer rank, String stepCode,
                                         String errorField, String errorMessage) throws FormValidationException {
        boolean alreadyDecided = execution.getStepsHistory().stream()
            .anyMatch(entry -> rank.equals(entry.getStepRankAtExecution())
                && stepCode.equals(entry.getStepCode()));

        if (alreadyDecided) {
            FormValidationException ex = new FormValidationException();
            ex.reject(errorField, errorMessage);
            throw ex;
        }
    }

    private void applyAbsenceCascade(RecruitmentExecutionDocument execution, @NonNull List<StepEntity> stepsAtRank,
                                     StepEntity absentStep, String evaluatedBy, LocalDateTime now) {
        Set<String> decidedCodes = resolveDecidedStepCodes(execution, execution.getCurrentRank());

        for (StepEntity step : stepsAtRank) {
            if (!decidedCodes.contains(step.getCode())) {
                String comment = "Recalé automatiquement suite à une absence sur \"" + absentStep.getName() + "\"";
                execution.getStepsHistory().add(
                    stepHistoryMapper.toEntry(step, StepDecision.KO, comment, evaluatedBy, now)
                );
            }
        }
    }

    private void applyDinedCascade(RecruitmentExecutionDocument execution, @NonNull List<StepEntity> stepsAtRank,
                                   StepEntity deniedStep, String evaluatedBy, LocalDateTime now) {
        Set<String> decidedCodes = resolveDecidedStepCodes(execution, execution.getCurrentRank());

        for (StepEntity step : stepsAtRank) {
            if (!decidedCodes.contains(step.getCode())) {
                String comment = "Recalé suite à une étape échouée \"" + deniedStep.getName() + "\"";
                execution.getStepsHistory().add(
                    stepHistoryMapper.toEntry(step, StepDecision.KO, comment, evaluatedBy, now)
                );
            }
        }
    }

    private void advanceRankIfComplete(RecruitmentExecutionDocument execution, ProcessEntity process,
                                       Integer currentRank, List<StepEntity> stepsAtRank) {
        if (!execution.isInProgress() || execution.getCurrentRank() == null) {
            return;
        }

        boolean shouldAdvance = isRankComplete(execution, currentRank, stepsAtRank)
            && stepsAtRank.size() == 1;

        if (!shouldAdvance) {
            return;
        }

        Optional<Integer> nextRank = stepResolver.resolveNextActiveRank(process, currentRank);
        execution.setCurrentRank(nextRank.orElse(null));
    }

    private void validateInProgress(RecruitmentExecutionDocument execution) throws FormValidationException {
        if (!execution.isInProgress()) {
            FormValidationException ex = new FormValidationException();
            ex.reject("status", "Cette exécution n'est plus en cours (déjà terminée)");
            throw ex;
        }
    }

    private void validateAwaitingBlockDecision(RecruitmentExecutionDocument execution) throws FormValidationException {
        if (!execution.isInProgress() || execution.getCurrentRank() == null) {
            FormValidationException ex = new FormValidationException();
            ex.reject(
                "status", "Cette exécution n'est pas en attente de décision sur un bloc de sous-étapes"
            );
            throw ex;
        }
    }

    private void validateAwaitingFinalDecision(RecruitmentExecutionDocument execution) throws FormValidationException {
        if (!execution.isInProgress() || execution.getCurrentRank() != null) {
            FormValidationException ex = new FormValidationException();
            ex.reject(
                "status", "Cette exécution n'est pas en attente de décision finale (toutes les étapes actives doivent d'abord être validées)"
            );
            throw ex;
        }
    }

    private void validateMultiStepRank(List<StepEntity> stepsAtRank) throws FormValidationException {
        if (stepsAtRank.size() <= 1) {
            FormValidationException ex = new FormValidationException();
            ex.reject(
                "rank", "Le rang courant ne comporte qu'une seule étape active : la décision de bloc ne s'applique qu'aux rangs à plusieurs étapes"
            );
            throw ex;
        }
    }

    // Retourne désormais le résultat du bulk (comment #3)
    @Override
    public List<RecruitmentExecutionResponseDTO> assignProcessToCandidates(UUID processId, List<UUID> candidateIds)
        throws ElementNotFoundException, MessageException, FormValidationException {
        log.info("Assigning process {} to {} candidates", processId, candidateIds.size());

        ProcessEntity process = findProcessOrThrow(processId.toString());
        List<CandidateEntity> candidates = candidateRepository.findAllById(candidateIds);

        if (candidates.size() != candidateIds.size()) {
            throw new ElementNotFoundException("Un ou plusieurs candidats sont introuvables");
        }

        return bulk(process, candidates).stream()
            .map(executionMapper::toDTO)
            .toList();
    }

    // Batché : une seule requête pour tous les candidats au lieu d'une par candidat (comment #1)
    private void ensureNoneBlacklisted(List<CandidateEntity> candidates) throws FormValidationException {
        List<UUID> candidateIds = candidates.stream().map(CandidateEntity::getId).toList();
        Set<UUID> blacklisted = blacklistRepository.findBlacklistedCandidateIds(candidateIds);

        if (!blacklisted.isEmpty()) {
            FormValidationException ex = new FormValidationException();
            ex.reject("candidateId", "Le(s) candidat(s) suivant(s) sont blacklistés : " + blacklisted);
            throw ex;
        }
    }

    // Batché : une seule requête pour tous les candidats au lieu d'une par candidat (comment #1)
    // NB : nécessite une méthode findByCandidateIdInAndProcessIdAndStatus sur executionRepository
    private void ensureNoneHaveActiveExecution(List<CandidateEntity> candidates, String processId) throws FormValidationException {
        List<String> candidateIds = candidates.stream().map(c -> c.getId().toString()).toList();

        Set<String> alreadyInProgress = executionRepository
            .findByCandidateIdInAndProcessIdAndStatus(candidateIds, processId, ExecutionStatus.IN_PROGRESS)
            .stream()
            .map(RecruitmentExecutionDocument::getCandidateId)
            .collect(Collectors.toSet());

        if (!alreadyInProgress.isEmpty()) {
            FormValidationException ex = new FormValidationException();
            ex.reject(
                "processId", "Un processus de recrutement est déjà en cours pour ce(s) candidat(s) sur ce process : " + alreadyInProgress
            );
            throw ex;
        }
    }

    private void ensureLastApplicationDateIsNow(LocalDateTime lastApplicationAt) throws FormValidationException {
        LocalDateTime now = LocalDateTime.now();
        LocalDate nowParse = now.toLocalDate();

        if (!nowParse.equals(lastApplicationAt.toLocalDate())) {
            throw FormValidationException.valueOf("lastApplicationAt", "La date de candidature doit correspondre à la date du jour");
        }
    }

    private List<RecruitmentExecutionDocument> bulk(ProcessEntity process, List<CandidateEntity> candidates)
        throws FormValidationException {

        String processIdValue = process.getId().toString();

        // Vérification en mémoire, pas de requête DB : on peut la garder par candidat
        for (CandidateEntity candidate : candidates) {
            ensureLastApplicationDateIsNow(candidate.getLastApplicationAt());
        }

        // Vérifications en base faites une seule fois pour tous les candidats
        ensureNoneBlacklisted(candidates);
        ensureNoneHaveActiveExecution(candidates, processIdValue);

        Integer firstRank = stepResolver.resolveFirstActiveRank(process);
        LocalDateTime now = LocalDateTime.now();
        List<RecruitmentExecutionDocument> executions = candidates.stream()
            .map(candidate -> executionMapper.toNewExecution(
                candidate.getId().toString(), processIdValue, firstRank, now))
            .toList();

        return executionRepository.saveAll(executions);
    }

}
