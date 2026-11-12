"""Pytest configuration and shared fixtures for ITV E2E Test Suite."""

import os
import sys
import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(TESTS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.core.ground_truth_loader import GroundTruthLoader, ProjectGroundTruth
from tests.core.prproj_parser import ParsedSequence, PrprojFastParser


@pytest.fixture(scope="session")
def project_kb118():
    truth = GroundTruthLoader.load_project_truth("kb118")
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse(target_sequence_name="kb118")
    return {"truth": truth, "seq": seq}


@pytest.fixture(scope="session")
def project_kb119():
    truth = GroundTruthLoader.load_project_truth("kb119")
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse(target_sequence_name="kb119")
    return {"truth": truth, "seq": seq}


@pytest.fixture(scope="session")
def project_kb120():
    truth = GroundTruthLoader.load_project_truth("kb120")
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse(target_sequence_name="kb120")
    return {"truth": truth, "seq": seq}


@pytest.fixture(scope="session")
def project_kb121():
    truth = GroundTruthLoader.load_project_truth("kb121")
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse(target_sequence_name="kb121")
    return {"truth": truth, "seq": seq}
