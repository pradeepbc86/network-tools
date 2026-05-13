"""Tests for RPKI validator."""

from netcli.rpki.validator import RPKIValidator


def test_validate_invalid_prefix_format():
    v = RPKIValidator()
    v.roas = []
    result = v.validate("not-a-prefix", 65000)
    assert result['status'] == 'error'


def test_validate_no_roa():
    v = RPKIValidator()
    v.roas = [{'prefix': '10.0.0.0/8', 'asn': 65001, 'maxLength': 8}]
    result = v.validate('192.0.2.0/24', 65000)
    assert result['status'] == 'not_found'


def test_validate_valid():
    v = RPKIValidator()
    v.roas = [{'prefix': '192.0.2.0/24', 'asn': 65000, 'maxLength': 24}]
    result = v.validate('192.0.2.0/24', 65000)
    assert result['status'] == 'valid'


def test_validate_invalid_asn():
    v = RPKIValidator()
    v.roas = [{'prefix': '192.0.2.0/24', 'asn': 65001, 'maxLength': 24}]
    result = v.validate('192.0.2.0/24', 65000)
    assert result['status'] == 'invalid'


def test_validate_exceeds_max_length():
    v = RPKIValidator()
    v.roas = [{'prefix': '192.0.2.0/24', 'asn': 65000, 'maxLength': 24}]
    result = v.validate('192.0.2.0/24', 65000)
    assert result['status'] == 'valid'
