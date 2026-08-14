from strongorc.convert import js_to_typed_ts


def test_js_to_typed_ts_types_args_and_rewrites_parent_imports() -> None:
    source = (
        'import { delta } from "../layer1/delta.js";\n'
        "export function echo(n) {\n"
        "  return delta(n) + 5;\n"
        "}\n"
    )
    typed = js_to_typed_ts(source)
    assert "echo(n: number): number" in typed
    assert 'from "../layer1/delta.ts"' in typed
    assert ".js" not in typed


def test_js_to_typed_ts_types_multi_arg_and_reexports() -> None:
    source = (
        'export { add } from "./add.js";\n'
        "export function sum3(a, b, c) {\n"
        "  return a + b + c;\n"
        "}\n"
    )
    typed = js_to_typed_ts(source)
    assert "sum3(a: number, b: number, c: number): number" in typed
    assert 'from "./add.ts"' in typed
