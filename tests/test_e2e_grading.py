"""端到端判分流水线测试。

不经过 HTTP，直接调用服务层，验证:
1. 图像预处理 + 锚点矫正能正确摆正答题卡
2. OMR 涂卡检测能识别学生涂的选项
3. 判分结果与"标准答案"比对后分数正确

前置条件: 先运行 scripts/gen_answer_sheet.py 生成测试图。
"""
import json
import sys
from pathlib import Path

# 将项目根目录加入 sys.path，保证 python tests/xxx.py 也能 import app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal, init_db
from app.models import ExamPaper, StudentSheet
from app.services.grading_dispatcher import grade_student_sheet


SAMPLE_DIR = Path("scripts/sample_data")


def _create_paper(db, template_obj: dict) -> ExamPaper:
    """创建测试试卷。template_obj 含 anchors + questions。"""
    questions = template_obj.get("questions", [])
    paper = ExamPaper(
        name="测试卷-选择题",
        subject="数学",
        template_json=template_obj,
        total_score=sum(q["score"] for q in questions),
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return paper


def test_end_to_end_grading():
    """完整的判分闭环测试。"""
    assert SAMPLE_DIR.exists(), (
        f"测试数据目录不存在: {SAMPLE_DIR}\n"
        "请先运行: python scripts/gen_answer_sheet.py"
    )

    template = json.loads((SAMPLE_DIR / "template.json").read_text(encoding="utf-8"))
    expected = json.loads((SAMPLE_DIR / "expected.json").read_text(encoding="utf-8"))
    sheet_path = str((SAMPLE_DIR / "sample_sheet_1.png").resolve())

    init_db()
    db = SessionLocal()
    try:
        paper = _create_paper(db, template)
        sheet = StudentSheet(
            paper_id=paper.id, original_path=sheet_path, status="pending"
        )
        db.add(sheet)
        db.commit()
        db.refresh(sheet)

        # 执行判分
        sheet = grade_student_sheet(db, sheet, paper)
        db.refresh(sheet)

        results = sorted(sheet.results, key=lambda r: int(r.question_no))

        # ---- 断言 ----
        # 1. 矫正后图已生成
        assert sheet.processed_path, "矫正图未生成"
        assert Path(sheet.processed_path).exists(), "矫正图文件不存在"

        # 2. 每道题都判了
        questions = template.get("questions", [])
        assert len(results) == len(questions), (
            f"判分题目数不匹配: 期望 {len(questions)}，实际 {len(results)}"
        )

        # 3. 检测出的答案与"学生真实作答"一致 (验证 OCR/OMR 识别准确)
        detected = [r.detected_answer for r in results]
        student_answers = expected["student_answers"]
        assert detected == student_answers, (
            f"识别答案与真实作答不一致:\n"
            f"  真实作答: {student_answers}\n"
            f"  识别结果: {detected}"
        )

        # 4. 总分正确 (与期望得分一致)
        assert sheet.total_score == expected["expected_score"], (
            f"总分不正确: 期望 {expected['expected_score']}, "
            f"实际 {sheet.total_score}"
        )

        # 5. 逐题判分正确 (用得分判断: final_score>=max_score 即答对)
        for r, student_ans, correct_ans in zip(
            results, student_answers, expected["correct_answers"]
        ):
            expected_correct = (student_ans == correct_ans)
            actual_correct = r.final_score >= r.max_score
            assert actual_correct == expected_correct, (
                f"题 {r.question_no} 判分错误: "
                f"学生={student_ans} 正确答案={correct_ans} "
                f"得分={r.final_score}/{r.max_score}"
            )

        # 打印结果
        print("\n" + "=" * 60)
        print("✓ 端到端判分测试通过！")
        print("=" * 60)
        print(f"试卷: {paper.name} (满分 {paper.total_score})")
        print(f"{'题号':<6}{'学生答案':<10}{'标准答案':<10}"
              f"{'检测':<8}{'得分':<8}{'结果'}")
        print("-" * 60)
        for r, student_ans, correct_ans in zip(
            results, student_answers, expected["correct_answers"]
        ):
            mark = "✓对" if r.final_score >= r.max_score else "✗错"
            print(f"{r.question_no:<6}{student_ans:<10}{correct_ans:<10}"
                  f"{r.detected_answer:<8}{r.final_score:<8}{mark}")
        print("-" * 60)
        print(f"总分: {sheet.total_score} / {paper.total_score}")
        print(f"需复核: {'是' if sheet.needs_review else '否'}")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    test_end_to_end_grading()
