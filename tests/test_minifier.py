import unittest

from pt.minifier import make_loader, minify_source


def _exec_minified(source: str) -> tuple[dict[str, object], dict[str, object]]:
    minified = minify_source(source)
    namespace = {"__name__": "__main__"}
    exec(minified, namespace)

    loader_namespace = {"__name__": "__main__"}
    exec(make_loader(minified, None), loader_namespace)
    return namespace, loader_namespace


class MinifierSafetyTests(unittest.TestCase):
    def test_framework_keyword_routes_and_methods_survive(self) -> None:
        source = r'''
routes = {}

def route(path):
    def deco(fn):
        routes[path] = fn
        return fn
    return deco

@route('/listsurvei/<survey_type>')
def listsurvei(survey_type):
    local_value = survey_type.upper()
    return local_value

class Worker:
    def helper(self):
        inner_value = 41
        return inner_value + 1

    def run(self):
        return self.helper()

def keyword_target(value):
    return value + 1

def keyword_caller():
    value = 2
    return keyword_target(value=value)

def closure():
    value = 5
    def inner():
        return value + 1
    return inner()
'''
        namespace, loader_namespace = _exec_minified(source)

        for current in (namespace, loader_namespace):
            self.assertEqual(
                current["routes"]["/listsurvei/<survey_type>"](survey_type="abc"),
                "ABC",
            )
            self.assertEqual(current["Worker"]().run(), 42)
            self.assertEqual(current["keyword_caller"](), 3)
            self.assertEqual(current["closure"](), 6)

    def test_dynamic_and_nonlocal_names_stay_stable(self) -> None:
        source = r'''
def nonlocal_closure():
    value = 1
    def inner():
        nonlocal value
        value += 4
    inner()
    return value

def dynamic_lookup():
    value = 9
    return eval('value')

def nested_dynamic_lookup():
    value = 12
    def inner():
        value
        return eval('value')
    return inner()

def lambda_dynamic_lookup():
    value = 13
    return (lambda: (value, eval('value'))[1])()
'''
        namespace, loader_namespace = _exec_minified(source)

        for current in (namespace, loader_namespace):
            self.assertEqual(current["nonlocal_closure"](), 5)
            self.assertEqual(current["dynamic_lookup"](), 9)
            self.assertEqual(current["nested_dynamic_lookup"](), 12)
            self.assertEqual(current["lambda_dynamic_lookup"](), 13)

    def test_method_flavors_and_generators_survive(self) -> None:
        source = r'''
class Tool:
    base = 10

    @staticmethod
    def static_value(value):
        local_value = value + 1
        return local_value

    @classmethod
    def class_value(cls, value):
        local_value = cls.base + value
        return local_value

    @property
    def prop_value(self):
        local_value = self.base + 5
        return local_value

def count_and_return():
    yield 1
    return 7

async def async_value(value):
    local_value = value + 3
    return local_value
'''
        namespace, loader_namespace = _exec_minified(source)

        for current in (namespace, loader_namespace):
            self.assertEqual(current["Tool"].static_value(4), 5)
            self.assertEqual(current["Tool"].class_value(4), 14)
            self.assertEqual(current["Tool"]().prop_value, 15)

            generator = current["count_and_return"]()
            self.assertEqual(next(generator), 1)
            with self.assertRaises(StopIteration) as raised:
                next(generator)
            self.assertEqual(raised.exception.value, 7)

            coroutine = current["async_value"](4)
            try:
                self.assertEqual(coroutine.send(None), 7)
            except StopIteration as done:
                self.assertEqual(done.value, 7)


if __name__ == "__main__":
    unittest.main()
