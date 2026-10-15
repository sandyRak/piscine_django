Voici uniquement les méthodes à corriger, avec l'explication de chaque changement.

## 1. Le problème N+1 (`ensureNotBlacklisted` + `ensureNoActiveExecution`)

**Pourquoi c'est un problème :** dans `bulk()`, tu bouclais sur chaque candidat et tu appelais `ensureNotBlacklisted(candidate.getId())` et `ensureNoActiveExecution(...)` à *chaque itération*. Donc pour 1000 candidats → 1000 requêtes vers la table blacklist + 1000 requêtes vers Mongo pour vérifier les exécutions en cours = 2000 requêtes. La bonne pratique est de sortir ces vérifications de la boucle et de les faire **une seule fois pour tout le lot**, en passant la liste complète des IDs.

**Avant (dans `bulk`) :**
```java
for (CandidateEntity candidate : candidates) {
    ensureLastApplicationDateIsNow(candidate.getLastApplicationAt());
    ensureNotBlacklisted(candidate.getId());
    ensureNoActiveExecution(candidate.getId().toString(), processIdValue);
}
```

**Après :**
```java
private List<RecruitmentExecutionDocument> bulk(ProcessEntity process, List<CandidateEntity> candidates)
    throws FormValidationException {

    String processIdValue = process.getId().toString();

    // Reste en boucle : c'est une vérification en mémoire (pas de requête DB), donc pas concernée par le N+1
    for (CandidateEntity candidate : candidates) {
        ensureLastApplicationDateIsNow(candidate.getLastApplicationAt());
    }

    // Sorties de la boucle : une seule requête chacune pour tout le lot
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
```

**Nouvelles méthodes batch (remplacent `ensureNotBlacklisted` et `ensureNoActiveExecution`) :**
```java
private void ensureNoneBlacklisted(List<CandidateEntity> candidates) throws FormValidationException {
    List<UUID> candidateIds = candidates.stream().map(CandidateEntity::getId).toList();
    Set<UUID> blacklisted = blacklistRepository.findBlacklistedCandidateIds(candidateIds);

    if (!blacklisted.isEmpty()) {
        FormValidationException ex = new FormValidationException();
        ex.reject("candidateId", "Le(s) candidat(s) suivant(s) sont blacklistés : " + blacklisted);
        throw ex;
    }
}

private void ensureNoneHaveActiveExecution(List<CandidateEntity> candidates, String processId) throws FormValidationException {
    List<String> candidateIds = candidates.stream().map(c -> c.getId().toString()).toList();

    Set<String> alreadyInProgress = executionRepository
        .findByCandidateIdInAndProcessIdAndStatus(candidateIds, processId, ExecutionStatus.IN_PROGRESS)
        .stream()
        .map(RecruitmentExecutionDocument::getCandidateId)
        .collect(Collectors.toSet());

    if (!alreadyInProgress.isEmpty()) {
        FormValidationException ex = new FormValidationException();
        ex.reject("processId", "Un processus de recrutement est déjà en cours pour ce(s) candidat(s) sur ce process : " + alreadyInProgress);
        throw ex;
    }
}
```

**Ce que ça implique côté repository :**
- `blacklistRepository.findBlacklistedCandidateIds(List<UUID>)` existe déjà et prend déjà une liste — donc rien à ajouter, il fallait juste arrêter de l'appeler candidat par candidat.
- `executionRepository` n'a probablement pas encore de méthode batch. Il faut l'ajouter dans `RecruitmentExecutionRepository` :
```java
List<RecruitmentExecutionDocument> findByCandidateIdInAndProcessIdAndStatus(
    List<String> candidateIds, String processId, ExecutionStatus status);
```
Si c'est du Spring Data MongoDB, cette signature suffit — Spring génère la requête automatiquement à partir du nom (`In` = clause IN sur `candidateId`).

---

## 2. Le doublon `mapper` / `executionMapper`

**Pourquoi c'est un problème :** les deux champs sont typés `RecruitmentExecutionMapper` et injectés via `@RequiredArgsConstructor` — donc Spring y injecte exactement le même bean deux fois sous deux noms différents. Ça n'a aucune utilité, ça prête à confusion (lequel utiliser ?) et ça alourdit le constructeur.

**Avant :**
```java
private final RecruitmentExecutionMapper mapper;
...
private final RecruitmentExecutionMapper executionMapper;
```

**Après :** on garde un seul champ, `executionMapper` (nom le plus explicite), et on remplace tous les `mapper.toDTO(...)` du fichier par `executionMapper.toDTO(...)`.
```java
private final RecruitmentExecutionMapper executionMapper;
```
Recherche/remplace dans le fichier : tous les appels `mapper.toDTO(...)` deviennent `executionMapper.toDTO(...)` (il y en a dans `start`, `recordDecision`, `recordBlockDecision`, `recordFinalDecision`).

---

## 3. `assignProcessToCandidates` doit retourner une liste

**Pourquoi :** actuellement la méthode calcule `bulk(process, candidates)` mais jette le résultat (`void`). Or `bulk` retourne déjà `List<RecruitmentExecutionDocument>` — c'est plus cohérent et plus utile pour l'appelant de renvoyer les exécutions créées (mappées en DTO), plutôt que de forcer un second appel pour les récupérer.

**Avant :**
```java
@Override
public void assignProcessToCandidates(UUID processId, List<UUID> candidateIds)
    throws ElementNotFoundException, MessageException, FormValidationException {
    log.info("Assigning process {} to {} candidates", processId, candidateIds.size());

    ProcessEntity process = findProcessOrThrow(processId.toString());
    List<CandidateEntity> candidates = candidateRepository.findAllById(candidateIds);

    if (candidates.size() != candidateIds.size()) {
        throw new ElementNotFoundException("Un ou plusieurs candidats sont introuvables");
    }

    bulk(process, candidates);
}
```

**Après :**
```java
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
```

**N'oublie pas de changer la signature dans l'interface** `RecruitmentExecutionCommandService` :
```java
List<RecruitmentExecutionResponseDTO> assignProcessToCandidates(UUID processId, List<UUID> candidateIds)
    throws ElementNotFoundException, MessageException, FormValidationException;
```

---

## 4. Renommer `checBlacklist` → `blacklistRepository`

**Pourquoi :** `checBlacklist` n'est pas explicite (faute de frappe probable pour "checkBlacklist", et le nom ne suit pas la convention `xxxRepository` des autres champs).

**Avant :**
```java
private final IRecruitmentBlacklistRepository checBlacklist;
```

**Après :**
```java
private final IRecruitmentBlacklistRepository blacklistRepository;
```
Et dans le corps de la méthode (maintenant fusionnée dans `ensureNoneBlacklisted` ci-dessus), remplace `checBlacklist.findBlacklistedCandidateIds(...)` par `blacklistRepository.findBlacklistedCandidateIds(...)`.