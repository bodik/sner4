# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
run password supervisor tests
"""

from sner.server.password_supervisor import PasswordSupervisor as PWS


def test_password_supervisor():
    """run test_password_supervisor unit tests"""

    # supervisor tests
    pwsr = PWS.check_strength('c')
    assert not pwsr.is_strong
    assert 'too short' in pwsr.message

    pwsr = PWS.check_strength('coverage01')
    assert not pwsr.is_strong
    assert 'classes found' in pwsr.message

    assert PWS.check_strength('Coverage0?').is_strong

    assert len(PWS.generate()) == 40
    assert len(PWS.generate_apikey()) == 64

    # encoder tests
    tmp_password = PWS.generate()
    tmp_hash = PWS.hash(tmp_password)
    assert PWS.compare(PWS.hash(tmp_password, PWS.get_salt(tmp_hash)), tmp_hash)

    assert len(PWS.hash_simple(PWS.generate())) == 128
