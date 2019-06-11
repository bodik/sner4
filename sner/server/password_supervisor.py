"""password supervisor service"""

import random
import re


class PasswordSupervisorResult():
    """classes wrapping password supervisor checks results"""

    def __init__(self, result, message):
        self._result = result
        self._message = message

    @property
    def is_strong(self):
        """iface getter"""

        return self._result

    @property
    def message(self):
        """getter"""

        return self._message


class PasswordSupervisor():
    """password supervisor implementation"""

    def __init__(self, min_length=10, min_classes=3):
        self.min_length = min_length
        self.min_classes = min_classes

    def check_strength(self, password, username=None):
        """checks password strength against configured policy"""

        # length
        if len(password) < self.min_length:
            return PasswordSupervisorResult(False, 'Password too short. At least %d characters required.' % self.min_length)

        # complexity
        classes = 0
        if re.search('[a-z]', password):
            classes += 1
        if re.search('[A-Z]', password):
            classes += 1
        if re.search('[0-9]', password):
            classes += 1
        if re.search('[^a-zA-Z0-9]', password):
            classes += 1
        if classes < self.min_classes:
            return PasswordSupervisorResult(
                False,
                'Only %d character classes found. At least %s classes required (lowercase, uppercase, digits, other).' % (classes, self.min_classes))

        # username similarity
        if username:
            for part in username.split('@'):
                if part.lower() in password.lower():
                    return PasswordSupervisorResult(False, 'Password must not be based on username.')

        return PasswordSupervisorResult(True, 'Password is according to policy.')

    def generate(self, length=40):
        """generates password compliant with the policy"""

        if length < self.min_length:
            raise RuntimeError('Requested less than configured minimum password length.')

        alphabet = ''.join([chr(x) for x in range(32, 126)])
        ret = ''
        while not self.check_strength(ret).is_strong:
            ret = ''
            for _ in range(length):
                ret += random.choice(alphabet)
        return ret


def test_all():
    """run all test cases"""

    pws = PasswordSupervisor()

    pwsr = pws.check_strength('x')
    assert not pwsr.is_strong
    assert 'too short' in pwsr.message

    pwsr = pws.check_strength('aaaaaaaaaA')
    assert not pwsr.is_strong
    assert 'classes found' in pwsr.message

    pwsr = pws.check_strength('Username1234', 'username')
    assert not pwsr.is_strong
    assert 'based on username' in pwsr.message

    assert pws.check_strength(pws.generate(), 'username').is_strong

    catched_without_pytest = False
    try:
        pws.generate(pws.min_length-1)
    except RuntimeError as e:
        assert str(e) == 'Requested less than configured minimum password length.'
        catched_without_pytest = True
    assert catched_without_pytest
