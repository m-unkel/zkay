import os
import shutil

from parameterized import parameterized_class

from zkay.compiler.privacy.zkay_frontend import compile_zkay
from zkay.examples.examples import all_examples
from zkay.tests.utils.test_examples import TestExamples

# get relevant paths
script_dir = os.path.dirname(os.path.realpath(__file__))
output_dir = os.path.join(script_dir, 'output')


@parameterized_class(('name', 'example'), all_examples)
class TestCompiler(TestExamples):

    def get_directory(self):
        d = os.path.join(output_dir, self.name)

        if os.path.isdir(d):
            shutil.rmtree(d)
        os.mkdir(d)

        return d

    def test_compilation_pipeline(self):
        c = self.example.code()
        d = self.get_directory()

        cg, code = compile_zkay(c, d, self.example.filename)

        self.assertIsNotNone(cg)
        self.assertIsNotNone(code)
        self.assertIn(self.example.name(), code)