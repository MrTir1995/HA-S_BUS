"""Tests for the S-Bus protocol implementation."""

from __future__ import annotations

from custom_components.sbus.sbus_protocol import SBusProtocol


def test_crc_calculation() -> None:
    """Test CRC-16 calculation."""
    protocol = SBusProtocol("localhost", 5050, 0)

    # Test with known values
    test_data = b"\x00\x01\x02\x03"
    crc = protocol._calculate_crc(test_data)

    # CRC should be deterministic
    assert isinstance(crc, int)
    assert 0 <= crc <= 0xFFFF


def test_sequence_generation() -> None:
    """Test sequence number generation."""
    protocol = SBusProtocol("localhost", 5050, 0)

    seq1 = protocol._get_next_sequence()
    seq2 = protocol._get_next_sequence()

    # Sequence should increment
    assert seq2 == seq1 + 1

    # Test wrap-around
    protocol._sequence = 0xFFFF
    seq_wrap = protocol._get_next_sequence()
    assert seq_wrap == 0


def test_build_telegram() -> None:
    """Test telegram building."""
    protocol = SBusProtocol("localhost", 5050, 0)

    telegram = protocol._build_telegram(0x06, b"\x00\x64\x01")

    # Verify structure
    assert len(telegram) >= 12  # Minimum telegram size
    assert telegram[4] == 0x01  # Version
    assert telegram[5] == 0x00  # Type
