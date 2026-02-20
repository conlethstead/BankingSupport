"""
Banking Support Agent - Evaluation Test Runner

Runs test cases through the workflow and generates accuracy reports.

Usage:
    python -m tests.test_runner                    # Run all tests
    python -m tests.test_runner --tag positive     # Run tests with specific tag
    python -m tests.test_runner --quick            # Run first 10 tests only
    python -m tests.test_runner --report report.md # Save report to file
"""

import sys
import json
import time
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from workflow.workflow import build_workflow, CONFIDENCE_THRESHOLD


@dataclass
class TestResult:
    """Result of a single test case."""
    test_id: str
    input_text: str
    expected_classification: str
    actual_classification: str
    expected_handler: str
    actual_handler: str
    expected_confidence_min: Optional[float]
    expected_confidence_max: Optional[float]
    actual_confidence: float
    expect_escalation: bool
    was_escalated: bool
    processing_time_ms: int
    classification_correct: bool
    handler_correct: bool
    confidence_in_range: bool
    escalation_correct: bool
    passed: bool
    error: Optional[str] = None
    tags: list = field(default_factory=list)


@dataclass
class EvaluationReport:
    """Aggregated evaluation metrics."""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    error_tests: int = 0
    
    classification_correct: int = 0
    classification_total: int = 0
    
    handler_correct: int = 0
    handler_total: int = 0
    
    escalation_correct: int = 0
    escalation_total: int = 0
    
    confidence_in_range: int = 0
    confidence_total: int = 0
    
    processing_times_ms: list = field(default_factory=list)
    
    by_classification: dict = field(default_factory=lambda: defaultdict(lambda: {"correct": 0, "total": 0}))
    by_tag: dict = field(default_factory=lambda: defaultdict(lambda: {"passed": 0, "total": 0}))
    
    failed_cases: list = field(default_factory=list)
    
    @property
    def classification_accuracy(self) -> float:
        return self.classification_correct / self.classification_total if self.classification_total else 0
    
    @property
    def handler_accuracy(self) -> float:
        return self.handler_correct / self.handler_total if self.handler_total else 0
    
    @property
    def escalation_accuracy(self) -> float:
        return self.escalation_correct / self.escalation_total if self.escalation_total else 0
    
    @property
    def confidence_accuracy(self) -> float:
        return self.confidence_in_range / self.confidence_total if self.confidence_total else 0
    
    @property
    def pass_rate(self) -> float:
        return self.passed_tests / self.total_tests if self.total_tests else 0
    
    @property
    def avg_processing_time_ms(self) -> float:
        return sum(self.processing_times_ms) / len(self.processing_times_ms) if self.processing_times_ms else 0
    
    @property
    def p50_processing_time_ms(self) -> float:
        if not self.processing_times_ms:
            return 0
        sorted_times = sorted(self.processing_times_ms)
        idx = len(sorted_times) // 2
        return sorted_times[idx]
    
    @property
    def p95_processing_time_ms(self) -> float:
        if not self.processing_times_ms:
            return 0
        sorted_times = sorted(self.processing_times_ms)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]


def load_test_cases(path: Path, tag_filter: Optional[str] = None) -> list[dict]:
    """Load test cases from JSON file, optionally filtering by tag."""
    with open(path) as f:
        data = json.load(f)
    
    cases = data.get("test_cases", [])
    
    if tag_filter:
        cases = [c for c in cases if tag_filter in c.get("tags", [])]
    
    return cases


def run_single_test(workflow, test_case: dict) -> TestResult:
    """Run a single test case through the workflow."""
    test_id = test_case["id"]
    input_text = test_case["input"]
    expected_classification = test_case["expected_classification"]
    expected_handler = test_case["expected_handler"]
    min_confidence = test_case.get("min_confidence")
    max_confidence = test_case.get("max_confidence")
    expect_escalation = test_case.get("expect_escalation", False)
    tags = test_case.get("tags", [])
    
    error = None
    actual_classification = ""
    actual_handler = ""
    actual_confidence = 0.0
    was_escalated = False
    processing_time_ms = 0
    
    try:
        result = workflow.invoke({
            "user_input": input_text,
            "customer_id": "TEST_USER",
            "customer_name": "Test User",
        })
        
        actual_classification = result.get("classified_type", "")
        actual_handler = result.get("agent_name", "")
        actual_confidence = result.get("classification_confidence", 0.0)
        processing_time_ms = result.get("processing_time_ms", 0)
        was_escalated = actual_handler == "EscalationAgent"
        
    except Exception as e:
        error = str(e)
    
    # Evaluate results
    classification_correct = actual_classification == expected_classification
    handler_correct = actual_handler == expected_handler
    
    # Confidence range check
    confidence_in_range = True
    if min_confidence is not None and actual_confidence < min_confidence:
        confidence_in_range = False
    if max_confidence is not None and actual_confidence > max_confidence:
        confidence_in_range = False
    
    # Escalation check
    escalation_correct = was_escalated == expect_escalation
    
    # Overall pass (classification and handler must be correct, escalation if expected)
    passed = classification_correct and handler_correct and (not expect_escalation or escalation_correct)
    if error:
        passed = False
    
    return TestResult(
        test_id=test_id,
        input_text=input_text,
        expected_classification=expected_classification,
        actual_classification=actual_classification,
        expected_handler=expected_handler,
        actual_handler=actual_handler,
        expected_confidence_min=min_confidence,
        expected_confidence_max=max_confidence,
        actual_confidence=actual_confidence,
        expect_escalation=expect_escalation,
        was_escalated=was_escalated,
        processing_time_ms=processing_time_ms,
        classification_correct=classification_correct,
        handler_correct=handler_correct,
        confidence_in_range=confidence_in_range,
        escalation_correct=escalation_correct,
        passed=passed,
        error=error,
        tags=tags,
    )


def run_evaluation(test_cases: list[dict], verbose: bool = True) -> tuple[list[TestResult], EvaluationReport]:
    """Run all test cases and generate evaluation report."""
    print(f"\n{'='*70}")
    print(f"🧪 BANKING SUPPORT AGENT - EVALUATION SUITE")
    print(f"{'='*70}")
    print(f"Running {len(test_cases)} test cases...")
    print(f"Confidence threshold for escalation: {CONFIDENCE_THRESHOLD}")
    print(f"{'='*70}\n")
    
    workflow = build_workflow()
    results: list[TestResult] = []
    report = EvaluationReport()
    
    for i, test_case in enumerate(test_cases, 1):
        if verbose:
            print(f"[{i}/{len(test_cases)}] {test_case['id']}: ", end="", flush=True)
        
        result = run_single_test(workflow, test_case)
        results.append(result)
        
        # Update report
        report.total_tests += 1
        report.classification_total += 1
        report.handler_total += 1
        
        if result.error:
            report.error_tests += 1
            if verbose:
                print(f"❌ ERROR: {result.error[:50]}")
        elif result.passed:
            report.passed_tests += 1
            if verbose:
                print(f"✅ PASS ({result.actual_classification}, {result.actual_confidence:.2f})")
        else:
            report.failed_tests += 1
            report.failed_cases.append(result)
            if verbose:
                issues = []
                if not result.classification_correct:
                    issues.append(f"class: {result.actual_classification}")
                if not result.handler_correct:
                    issues.append(f"handler: {result.actual_handler}")
                if not result.escalation_correct:
                    issues.append(f"escalation: {result.was_escalated}")
                print(f"❌ FAIL ({', '.join(issues)})")
        
        if result.classification_correct:
            report.classification_correct += 1
        if result.handler_correct:
            report.handler_correct += 1
        
        # Escalation tracking
        if result.expect_escalation or result.was_escalated:
            report.escalation_total += 1
            if result.escalation_correct:
                report.escalation_correct += 1
        
        # Confidence tracking
        if result.expected_confidence_min is not None or result.expected_confidence_max is not None:
            report.confidence_total += 1
            if result.confidence_in_range:
                report.confidence_in_range += 1
        
        # Processing time
        if result.processing_time_ms > 0:
            report.processing_times_ms.append(result.processing_time_ms)
        
        # By classification
        report.by_classification[result.expected_classification]["total"] += 1
        if result.classification_correct:
            report.by_classification[result.expected_classification]["correct"] += 1
        
        # By tag
        for tag in result.tags:
            report.by_tag[tag]["total"] += 1
            if result.passed:
                report.by_tag[tag]["passed"] += 1
    
    return results, report


def print_report(report: EvaluationReport) -> str:
    """Generate and print the evaluation report."""
    lines = []
    
    lines.append(f"\n{'='*70}")
    lines.append(f"📊 EVALUATION REPORT")
    lines.append(f"{'='*70}\n")
    
    # Overall metrics
    lines.append(f"## Overall Results")
    lines.append(f"- Total tests: {report.total_tests}")
    lines.append(f"- Passed: {report.passed_tests} ({report.pass_rate*100:.1f}%)")
    lines.append(f"- Failed: {report.failed_tests}")
    lines.append(f"- Errors: {report.error_tests}")
    lines.append("")
    
    # Accuracy metrics
    lines.append(f"## Accuracy Metrics")
    lines.append(f"- Classification accuracy: {report.classification_accuracy*100:.1f}% ({report.classification_correct}/{report.classification_total})")
    lines.append(f"- Handler routing accuracy: {report.handler_accuracy*100:.1f}% ({report.handler_correct}/{report.handler_total})")
    if report.escalation_total > 0:
        lines.append(f"- Escalation accuracy: {report.escalation_accuracy*100:.1f}% ({report.escalation_correct}/{report.escalation_total})")
    if report.confidence_total > 0:
        lines.append(f"- Confidence calibration: {report.confidence_accuracy*100:.1f}% ({report.confidence_in_range}/{report.confidence_total})")
    lines.append("")
    
    # Performance metrics
    if report.processing_times_ms:
        lines.append(f"## Performance")
        lines.append(f"- Avg processing time: {report.avg_processing_time_ms:.0f} ms")
        lines.append(f"- P50 processing time: {report.p50_processing_time_ms:.0f} ms")
        lines.append(f"- P95 processing time: {report.p95_processing_time_ms:.0f} ms")
        lines.append("")
    
    # By classification breakdown
    lines.append(f"## Accuracy by Classification Type")
    for cls_type, stats in sorted(report.by_classification.items()):
        acc = stats["correct"] / stats["total"] * 100 if stats["total"] else 0
        lines.append(f"- {cls_type}: {acc:.1f}% ({stats['correct']}/{stats['total']})")
    lines.append("")
    
    # By tag breakdown (top tags)
    if report.by_tag:
        lines.append(f"## Pass Rate by Tag (top 10)")
        sorted_tags = sorted(report.by_tag.items(), key=lambda x: x[1]["total"], reverse=True)[:10]
        for tag, stats in sorted_tags:
            rate = stats["passed"] / stats["total"] * 100 if stats["total"] else 0
            lines.append(f"- {tag}: {rate:.1f}% ({stats['passed']}/{stats['total']})")
        lines.append("")
    
    # Failed cases summary
    if report.failed_cases:
        lines.append(f"## Failed Cases ({len(report.failed_cases)})")
        for result in report.failed_cases[:10]:  # Show first 10
            lines.append(f"\n### {result.test_id}")
            lines.append(f"- Input: \"{result.input_text[:60]}...\"" if len(result.input_text) > 60 else f"- Input: \"{result.input_text}\"")
            lines.append(f"- Expected: {result.expected_classification} → {result.expected_handler}")
            lines.append(f"- Actual: {result.actual_classification} → {result.actual_handler} (conf: {result.actual_confidence:.2f})")
            if result.expect_escalation:
                lines.append(f"- Expected escalation: {result.expect_escalation}, Got: {result.was_escalated}")
        if len(report.failed_cases) > 10:
            lines.append(f"\n... and {len(report.failed_cases) - 10} more failed cases")
        lines.append("")
    
    lines.append(f"{'='*70}")
    
    report_text = "\n".join(lines)
    print(report_text)
    return report_text


def main():
    parser = argparse.ArgumentParser(description="Run Banking Support Agent evaluation tests")
    parser.add_argument("--tag", type=str, help="Filter tests by tag (e.g., 'positive', 'edge_case')")
    parser.add_argument("--quick", action="store_true", help="Run only first 10 tests")
    parser.add_argument("--report", type=str, help="Save report to file (e.g., report.md)")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-test output")
    parser.add_argument("--test-file", type=str, default="tests/test_cases.json", help="Path to test cases JSON")
    args = parser.parse_args()
    
    test_file = PROJECT_ROOT / args.test_file
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        sys.exit(1)
    
    test_cases = load_test_cases(test_file, tag_filter=args.tag)
    
    if args.quick:
        test_cases = test_cases[:10]
    
    if not test_cases:
        print("❌ No test cases found matching criteria")
        sys.exit(1)
    
    results, report = run_evaluation(test_cases, verbose=not args.quiet)
    report_text = print_report(report)
    
    if args.report:
        report_path = PROJECT_ROOT / args.report
        with open(report_path, "w") as f:
            f.write(report_text)
        print(f"\n📄 Report saved to: {report_path}")
    
    # Exit with error code if tests failed
    if report.failed_tests > 0 or report.error_tests > 0:
        sys.exit(1)
    
    print("\n✅ All tests passed!")
    sys.exit(0)


if __name__ == "__main__":
    main()
