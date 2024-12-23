import unittest
from io import StringIO

from transpile import to_python

class TestTranspile(unittest.TestCase):
    def test_replace_token_is(self):
        src = StringIO(
            "C is CC # comment 1\n"
            "D is CD#\n"
            "E is CE\n"
            "# comment 2\n"
            "a = '#' #\n"
            "b = \"\"\n"
            "F is CF"
        )
        res = (
            "C:__yp__.theory = __yp__.category(CC) # comment 1\n"
            "D:__yp__.theory = __yp__.category(CD)#\n"
            "E:__yp__.theory = __yp__.category(CE)\n"
            "# comment 2\n"
            "a = '#' #\n"
            "b = \"\"\n"
            "F:__yp__.theory = __yp__.category(CF)"
        )
        dst = StringIO()
        to_python(dst, src)
        dst.seek(0)
        self.assertEqual(src.read(), res)

    def test_replace_token_backtick(self):
        src = StringIO(
            "a = `b` @ f(\"c\") # `b`\n" \
            "b = f(\"c\") @ `a`\n" \
            "\n" \
            "class A:\n" \
            "    X: C\n" \
            "    Y: C\n" \
            "    x: `X`\n" \
            "    y: `Y`\n" \
            "    f: `X` >> `Y`\n" \
            "    g: F[`X`] >> F[`Y`]"
        )
        res = (
            "a = __yp__.ref('b') @ f(\"c\") # `b`\n" \
            "b = f(\"c\") @ __yp__.ref('a')\n" \
            "\n" \
            "class A(__yp__.base()):\n" \
            "    X: C\n" \
            "    Y: C\n" \
            "    x: __yp__.ref('X')\n" \
            "    y: __yp__.ref('Y')\n" \
            "    f: __yp__.ref('X') >> __yp__.ref('Y')\n" \
            "    g: F[__yp__.ref('X')] >> F[__yp__.ref('Y')]"
        )
        dst = StringIO()
        to_python(dst, src)
        dst.seek(0)
        self.assertEqual(src.read(), res)

    def test_handle_class(self):
        src = StringIO(
            "class A!:\n" \
            "    # X: C\n" \
            "    x: `X`\n" \
            "    y: \"`Y`\"\n" \
            "\n" \
            "class B!(A, C):\n" \
            "    pass # comment\n" \
            "class C<!: \\" \
            "    pass" \
            "class D>!: pass" \
            "class E: pass" \
            "class F(E): a: X" \
            "class\\" \
            "    G: pass" \
            "\\" \
            "class H(')'): pass" \
            "#class I: pass" \
            "class J((),(('('),()),')))',): pass" \
        )
        res = (
            "a = __yp__.ref('b') @ f(\"c\") # `b`" \
            "b = f(\"c\") @ __yp__.ref('a')" \
            "" \
            "class A(__yp__.base()):" \
            "    X: C" \
            "    Y: C" \
            "    x: __yp__.ref('X')" \
            "    y: __yp__.ref('Y')" \
            "    f: __yp__.ref('X') >> __yp__.ref('Y')" \
            "    g: F[__yp__.ref('X')] >> F[__yp__.ref('Y')]"
            "class C(__yp__.base_unique()): \\" \
            "    pass" \
            "class D(__yp__.base_exists()): pass" \
            "class E(__yp__.base()): pass" \
            "class F(__yp__.base(E)): a: X" \
            "class\\" \
            "    G(__yp__.base()): pass" \
            "\\" \
            "class H(__yp__.base(')')): pass" \
            "#class I: pass" \
            "class J(__yp__.base((),(('('),()),')))',)): pass" \
        )
        dst = StringIO()
        to_python(dst, src)
        dst.seek(0)
        self.assertEqual(src.read(), res)
