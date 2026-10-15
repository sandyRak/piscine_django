#!/usr/bin/python3

from elem import Elem, Text


class Html(Elem):
    def __init__(self, content=None, attr=None):
        super().__init__('html', attr or {}, content)


class Head(Elem):
    def __init__(self, content=None, attr=None):
        super().__init__('head', attr or {}, content)


class Body(Elem):
    def __init__(self, content=None, attr=None):
        super().__init__('body', attr or {}, content)


class Title(Elem):
    def __init__(self, content=None, attr=None):
        super().__init__('title', attr or {}, content)


class Meta(Elem):
    def __init__(self, attr=None):
        super().__init__('meta', attr or {}, None, 'simple')


class Img(Elem):
    def __init__(self, attr=None):
        super().__init__('img', attr or {}, None, 'simple')


class Table(Elem):
    def __init__(self, content=None, attr=None):
        super().__init__('table', attr or {}, content)


class Th(Elem):
    def __init__(self, content=None, attr=None):
        super().__init__('th', attr or {}, content)


class Tr(Elem):
    def __init__(self, content=None, attr=None):
        super().__init__('tr', attr or {}, content)


class Td(Elem):
    def __init__(self, content=None, attr=None):
        super().__init__('td', attr or {}, content)


class Ul(Elem):
    def __init__(self, content=None, attr=None):
        super().__init__('ul', attr or {}, content)


class Ol(Elem):
    def __init__(self, content=None, attr=None):
        super().__init__('ol', attr or {}, content)


class Li(Elem):
    def __init__(self, content=None, attr=None):
        super().__init__('li', attr or {}, content)


class H1(Elem):
    def __init__(self, content=None, attr=None):
        super().__init__('h1', attr or {}, content)


class H2(Elem):
    def __init__(self, content=None, attr=None):
        super().__init__('h2', attr or {}, content)


class P(Elem):
    def __init__(self, content=None, attr=None):
        super().__init__('p', attr or {}, content)


class Div(Elem):
    def __init__(self, content=None, attr=None):
        super().__init__('div', attr or {}, content)


class Span(Elem):
    def __init__(self, content=None, attr=None):
        super().__init__('span', attr or {}, content)


class Hr(Elem):
    def __init__(self, attr=None):
        super().__init__('hr', attr or {}, None, 'simple')


class Br(Elem):
    def __init__(self, attr=None):
        super().__init__('br', attr or {}, None, 'simple')


def build_page():
    """La page de l'ex04, refaite avec les classes dérivées."""
    return Html([
        Head(Title(Text('"Hello ground!"'))),
        Body([
            H1(Text('"Oh no, not again!"')),
            Img({'src': 'http://i.imgur.com/pfp3T.jpg'}),
        ]),
    ])


def run_tests():
    assert str(Html([Head(), Body()])) == (
        '<html>\n  <head></head>\n  <body></body>\n</html>')
    assert str(Head(Title(Text('Hi')))) == (
        '<head>\n  <title>\n    Hi\n  </title>\n</head>')

    assert str(Meta({'charset': 'utf-8'})) == '<meta charset="utf-8" />'
    assert str(Img({'src': 'a.jpg'})) == '<img src="a.jpg" />'
    assert str(Hr()) == '<hr />'
    assert str(Br()) == '<br />'

    assert str(P(Text('Salut'))) == '<p>\n  Salut\n</p>'
    assert str(Div(attr={'id': 'x'})) == '<div id="x"></div>'
    assert str(Span(Text('a'))) == '<span>\n  a\n</span>'
    assert str(H1(Text('T'))) == '<h1>\n  T\n</h1>'
    assert str(H2(Text('T'))) == '<h2>\n  T\n</h2>'
    assert str(Body(Text('b'))) == '<body>\n  b\n</body>'

    assert str(Ul([Li(Text('a')), Li(Text('b'))])) == (
        '<ul>\n  <li>\n    a\n  </li>\n  <li>\n    b\n  </li>\n</ul>')
    assert str(Ol(Li(Text('a')))) == '<ol>\n  <li>\n    a\n  </li>\n</ol>'

    assert str(Table(Tr([Th(Text('h')), Td(Text('d'))]))) == (
        '<table>\n  <tr>\n    <th>\n      h\n    </th>\n'
        '    <td>\n      d\n    </td>\n  </tr>\n</table>')

    assert str(Div(attr={'id': 'x', 'class': 'c'})) == (
        '<div class="c" id="x"></div>')

    try:
        P('texte simple')
        raise AssertionError('ValidationError attendue')
    except Elem.ValidationError:
        pass

    print('Tous les tests : OK.')


if __name__ == '__main__':
    run_tests()
    print(build_page())