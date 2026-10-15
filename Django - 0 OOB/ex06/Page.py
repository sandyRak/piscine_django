#!/usr/bin/python3

from elem import Elem, Text
from elements import (Html, Head, Body, Title, Meta, Img, Table, Th, Tr, Td,
                      Ul, Ol, Li, H1, H2, P, Div, Span, Hr, Br)


class Page:
    """Une page HTML dont on peut valider la structure."""

    ALLOWED = (Html, Head, Body, Title, Meta, Img, Table, Th, Tr, Td,
               Ul, Ol, Li, H1, H2, P, Div, Span, Hr, Br, Text)

    def __init__(self, elem):
        if not isinstance(elem, Elem):
            raise TypeError('Page needs an instance of a class '
                            'inheriting from Elem.')
        self.elem = elem

    @staticmethod
    def _all_of(children, types):
        """True si tous les enfants sont d'un des types donnés."""
        return all(isinstance(child, types) for child in children)

    @staticmethod
    def _only_text(children):
        """True si il y a exactement un enfant, et c'est un Text."""
        return len(children) == 1 and isinstance(children[0], Text)

    @staticmethod
    def _check_node(node):
        """Vérifie un nœud et, récursivement, tous ses descendants."""
        if isinstance(node, Text):
            return True
        if not isinstance(node, Page.ALLOWED):
            return False

        children = node.content

        if isinstance(node, Html):
            ok = (len(children) == 2
                  and isinstance(children[0], Head)
                  and isinstance(children[1], Body))
        elif isinstance(node, Head):
            ok = len(children) == 1 and isinstance(children[0], Title)
        elif isinstance(node, (Body, Div)):
            ok = Page._all_of(children,
                              (H1, H2, Div, Table, Ul, Ol, Span, Text))
        elif isinstance(node, (Title, H1, H2, Li, Th, Td)):
            ok = Page._only_text(children)
        elif isinstance(node, P):
            ok = Page._all_of(children, Text)
        elif isinstance(node, Span):
            ok = Page._all_of(children, (Text, P))
        elif isinstance(node, (Ul, Ol)):
            ok = len(children) >= 1 and Page._all_of(children, Li)
        elif isinstance(node, Tr):
            ok = len(children) >= 1 and (Page._all_of(children, Th)
                                         or Page._all_of(children, Td))
        elif isinstance(node, Table):
            ok = Page._all_of(children, Tr)
        else:
            # Meta, Img, Hr, Br : aucune contrainte de contenu
            ok = True

        return ok and all(Page._check_node(child) for child in children)

    def is_valid(self):
        return Page._check_node(self.elem)

    def __str__(self):
        result = str(self.elem)
        if isinstance(self.elem, Html):
            result = '<!DOCTYPE html>\n' + result
        return result

    def write_to_file(self, filename):
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(str(self))

def run_tests():
    # ---------- Pages valides ----------
    good_html = Html([Head(Title(Text('Titre'))),
                      Body([H1(Text('Hello')),
                            Div([Span([P(Text('a')), Text('b')])]),
                            Ul([Li(Text('x')), Li(Text('y'))]),
                            Table(Tr([Th(Text('h')), Th(Text('i'))])),
                            Table(Tr([Td(Text('d'))]))])])
    assert Page(good_html).is_valid()
    assert Page(Div()).is_valid()
    assert Page(P(Text('texte'))).is_valid()
    assert Page(Img({'src': 'a.jpg'})).is_valid()
    assert Page(Br()).is_valid()

    # ---------- Type d'élément non autorisé ----------
    assert not Page(Elem('section')).is_valid()
    assert not Page(Div(Elem('section'))).is_valid()

    # ---------- Html ----------
    assert not Page(Html()).is_valid()
    assert not Page(Html(Head(Title(Text('t'))))).is_valid()
    assert not Page(Html([Body(), Head(Title(Text('t')))])).is_valid()
    assert not Page(Html([Head(Title(Text('t'))), Body(),
                          Body()])).is_valid()

    # ---------- Head ----------
    assert not Page(Head()).is_valid()
    assert not Page(Head([Title(Text('a')), Title(Text('b'))])).is_valid()
    assert not Page(Head([Title(Text('a')), Meta()])).is_valid()
    assert not Page(Head(Text('a'))).is_valid()

    # ---------- Body et Div ----------
    assert Page(Body([H1(Text('a')), H2(Text('b')), Text('c')])).is_valid()
    assert not Page(Body(P(Text('a')))).is_valid()
    assert not Page(Div(Li(Text('a')))).is_valid()
    assert not Page(Div(Img())).is_valid()
    assert not Page(Div(Div(P(Text('a'))))).is_valid()

    # ---------- Title, H1, H2, Li, Th, Td ----------
    for cls in (Title, H1, H2, Li, Th, Td):
        assert Page(cls(Text('a'))).is_valid()
        assert not Page(cls()).is_valid()
        assert not Page(cls([Text('a'), Text('b')])).is_valid()
        assert not Page(cls(Span())).is_valid()

    # ---------- P ----------
    assert Page(P()).is_valid()
    assert Page(P([Text('a'), Text('b')])).is_valid()
    assert not Page(P(Span())).is_valid()

    # ---------- Span ----------
    assert Page(Span([Text('a'), P(Text('b'))])).is_valid()
    assert not Page(Span(Div())).is_valid()

    # ---------- Ul et Ol ----------
    assert Page(Ol(Li(Text('a')))).is_valid()
    assert not Page(Ul()).is_valid()
    assert not Page(Ol()).is_valid()
    assert not Page(Ul([Li(Text('a')), Text('b')])).is_valid()
    assert not Page(Ul(Div())).is_valid()

    # ---------- Tr ----------
    assert Page(Tr([Th(Text('a')), Th(Text('b'))])).is_valid()
    assert Page(Tr([Td(Text('a')), Td(Text('b'))])).is_valid()
    assert not Page(Tr()).is_valid()
    assert not Page(Tr([Th(Text('a')), Td(Text('b'))])).is_valid()
    assert not Page(Tr(Li(Text('a')))).is_valid()

    # ---------- Table ----------
    assert Page(Table(Tr(Td(Text('a'))))).is_valid()
    assert not Page(Table(Td(Text('a')))).is_valid()
    assert not Page(Table(Text('a'))).is_valid()

    # ---------- Erreur profonde : elle remonte jusqu'à la racine ----------
    deep = Html([Head(Title(Text('t'))),
                 Body(Div(Div(Ul(Li(Span()))))) ])
    assert not Page(deep).is_valid()

    # ---------- Constructeur ----------
    try:
        Page('pas un Elem')
        raise AssertionError('TypeError attendue')
    except TypeError:
        pass

    # ---------- Doctype : seulement si la racine est Html ----------
    page_html = Page(Html([Head(Title(Text('t'))), Body()]))
    assert str(page_html).startswith('<!DOCTYPE html>\n<html>')
    assert str(Page(Div())) == '<div></div>'
    assert 'DOCTYPE' not in str(Page(Body()))

    # ---------- Écriture dans un fichier ----------
    filename = 'test_output.html'
    page_html.write_to_file(filename)
    with open(filename, 'r', encoding='utf-8') as file:
        assert file.read() == str(page_html)
    Page(Div(P(Text('x')))).write_to_file(filename)
    with open(filename, 'r', encoding='utf-8') as file:
        assert file.read() == '<div>\n  <p>\n    x\n  </p>\n</div>'

    print('Tous les tests : OK.')


if __name__ == '__main__':
    run_tests()
    print(Page(Html([Head(Title(Text('Hello'))),
                     Body(H1(Text('Salut')))])))