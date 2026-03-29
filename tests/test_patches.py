from layai_reforge.models.program import ProgramPatchOp, TaskAgentSpec, ToolDescriptor, UnifiedProgram
from layai_reforge.patches import apply_patches


def test_apply_set_system_prompt():
    p = UnifiedProgram(task=TaskAgentSpec(system_prompt="a"))
    out = apply_patches(p, [ProgramPatchOp(op="set_system_prompt", value="b")])
    assert out.task.system_prompt == "b"


def test_add_remove_tool():
    p = UnifiedProgram(
        task=TaskAgentSpec(
            tools=[ToolDescriptor(name="t1"), ToolDescriptor(name="t2")],
        )
    )
    out = apply_patches(p, [ProgramPatchOp(op="remove_tool", value="t1")])
    assert [t.name for t in out.task.tools] == ["t2"]
