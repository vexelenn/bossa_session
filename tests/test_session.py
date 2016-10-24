"""Tests for the bossa_session module."""

import pytest

from bossa_session.session import BossaSession


@pytest.mark.parametrize('key, price, expected_price', (
    ('TESTKEY', '17BB2E2CE01443B1', '5.000000'),
    ('TESTKEY', 'BDE2D5D23094593E', '3.750000'),
    ('ImaKey', 'B209A29D062226F9', '3.750000'),
    ('ImaKey', 'B6DE817F557879BC', '5.000000'),
))
def test_price_correct(key, price, expected_price):
    """Test price decryption."""
    # TODO mock session here


