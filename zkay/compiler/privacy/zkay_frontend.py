import json
import os
from copy import deepcopy
import shutil
import tempfile
import pathlib
import uuid

from zkay.compiler.privacy import library_contracts
from zkay.compiler.privacy.circuit_generation.backends.zokrates_generator import ZokratesGenerator
from zkay.compiler.privacy.circuit_generation.circuit_generator import CircuitGenerator
from zkay.compiler.privacy.manifest import Manifest
from zkay.compiler.privacy.proving_schemes.gm17 import ProvingSchemeGm17
from zkay.compiler.privacy.proving_schemes.proving_scheme import ProvingScheme
from zkay.compiler.privacy.transformer.zkay_transformer import transform_ast
from zkay.compiler.solidity.compiler import compile_solidity
from zkay.utils.progress_printer import print_step
from zkay.zkay_ast.ast import AST


def compile_zkay(ast: AST, output_dir: str, filename: str, get_binaries: bool = True):
    ast, zkt = transform_ast(deepcopy(ast))

    # Write public contract file
    with print_step('Generating solidity code'):
        with open(os.path.join(output_dir, filename), 'w') as f:
            f.write(ast.code())

        # Write pki contract
        with open(os.path.join(output_dir, f'{library_contracts.pki_contract_name}.sol'), 'w') as f:
            f.write(library_contracts.pki_contract)

        # Write library contract
        with open(os.path.join(output_dir, ProvingScheme.verify_libs_contract_filename), 'w') as f:
            f.write(library_contracts.get_verify_libs_code())

    ps = ProvingSchemeGm17()
    cg = ZokratesGenerator(ast, list(zkt.circuit_generators.values()), ps, output_dir)

    # Generate manifest
    manifest = {
        Manifest.uuid: uuid.uuid1().hex,
        Manifest.contract_filename: filename,
        Manifest.proving_scheme: ps.name,
        Manifest.pki_lib: f'{library_contracts.pki_contract_name}.sol',
        Manifest.verify_lib: ProvingScheme.verify_libs_contract_filename,
        Manifest.verifier_names: {
            f'{cc.fct.parent.idf.name}.{cc.fct.name}': cc.verifier_contract.contract_type.type_name.names[0].name for cc in
            cg.circuits_to_prove
        }
    }
    with open(os.path.join(output_dir, 'manifest.json'), 'w') as f:
        f.write(json.dumps(manifest))

    # Generate circuits and corresponding verification contracts
    cg.generate_circuits(import_keys=False)

    if get_binaries:
        with print_step('Compiling evm binaries'):
            compile_solidity(output_dir, filename)
            for vc in cg.get_verification_contract_filenames():
                compile_solidity(output_dir, os.path.split(vc)[1])

    return cg


def package_zkay(zkay_input_filename: str, cg: CircuitGenerator):
    with print_step('Packaging for distribution'):
        # create archive with zkay code + all verification and prover keys
        root = pathlib.Path(cg.output_dir)
        infile = pathlib.Path(zkay_input_filename)
        manifestfile = root.joinpath("manifest.json")
        filenames = [pathlib.Path(p) for p in cg.get_all_key_paths()]
        for p in filenames + [infile, manifestfile]:
            if not p.exists():
                raise FileNotFoundError()

        tmpdir = tempfile.mkdtemp()
        shutil.copyfile(infile, os.path.join(tmpdir, infile.name))
        shutil.copyfile(manifestfile, os.path.join(tmpdir, manifestfile.name))
        for p in filenames:
            pdir = os.path.join(tmpdir, p.relative_to(root).parent)
            if not os.path.exists(pdir):
                os.makedirs(pdir)
            shutil.copyfile(p.absolute(), os.path.join(tmpdir, p.relative_to(root)))

        output_basename = infile.name.replace('.sol', '')

        shutil.make_archive(os.path.join(cg.output_dir, output_basename), 'zip', tmpdir)
        shutil.rmtree(tmpdir)

        os.rename(os.path.join(cg.output_dir, f'{output_basename}.zip'), os.path.join(cg.output_dir, f'{output_basename}.zkpkg'))


def import_pkg(filename: str):
    pass