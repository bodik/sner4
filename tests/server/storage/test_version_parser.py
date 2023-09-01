import unittest
from version_parser import parse, is_in_version_range, InvalidFormatException


class Test(unittest.TestCase):
    def test_invalid_version(self) -> None:
        with self.assertRaises(InvalidFormatException):
            parse("3.0")
        with self.assertRaises(InvalidFormatException):
            parse("!3.0")
        with self.assertRaises(InvalidFormatException):
            parse("p3.0")
        # These should be parsed without an Exception:
        parse("!=3.0")
        parse("==3.0")
        parse("  =3.0")
        parse("=3.0")
        parse(" =3.0    ;  =4.0")
        parse(">=3.0")
        parse("   >3.0")
        parse(" <=3.0 ")
        parse("<3.0")

    def test_is_in_version_range(self) -> None:
        version_spec = parse(">=3.0 ,  <4.0; =5.0 ")
        self.assertFalse(is_in_version_range("5.1", "", version_spec))
        self.assertFalse(is_in_version_range("4.0", "", version_spec))
        self.assertFalse(is_in_version_range("2.3", "", version_spec))
        self.assertTrue(is_in_version_range("5.0", "", version_spec))
        self.assertTrue(is_in_version_range("3.0", "", version_spec))
        self.assertTrue(is_in_version_range("3.8", "", version_spec))
        self.assertTrue(is_in_version_range("3.3.3", "", version_spec))

        version_spec = parse("  >=3.0, <3.3; >=5.0.0")
        self.assertTrue(is_in_version_range("3.0", "", version_spec))
        self.assertTrue(is_in_version_range("3.1.3", "", version_spec))
        self.assertTrue(is_in_version_range("3.2.5", "", version_spec))
        self.assertTrue(is_in_version_range("5.0.1", "", version_spec))
        self.assertTrue(is_in_version_range("7.1.0", "", version_spec))
        self.assertFalse(is_in_version_range("3.3", "", version_spec))
        self.assertFalse(is_in_version_range("3.4", "", version_spec))
        self.assertFalse(is_in_version_range("2.0", "", version_spec))
        self.assertFalse(is_in_version_range("1.3.5", "", version_spec))
        self.assertFalse(is_in_version_range("4.2", "", version_spec))

        # Debian patches.
        version_spec = parse(">4.0")
        self.assertTrue(is_in_version_range("4.0p1", "", version_spec))
        self.assertTrue(is_in_version_range("4.0p1 Debianblablabla", "",
                                            version_spec))
        self.assertFalse(is_in_version_range("4.0",  "", version_spec))

    def test_rhel_versions(self):
        version_spec = parse(">=0.0")
        self.assertFalse(is_in_version_range("4.0", "(CentOS) PHP/5.4.16", version_spec))
        self.assertFalse(is_in_version_range("4.0", "(CENTOS) PHP/5.4.16", version_spec))
        self.assertFalse(is_in_version_range("4.0", "(centos) PHP/5.4.16", version_spec))
        self.assertFalse(is_in_version_range("4.0", "(Scientific Linux) OpenSSL", version_spec))
        self.assertFalse(is_in_version_range("4.0", "(Red Hat Enterprise Linux) OpenSSL/1.1.1k", version_spec))
        self.assertFalse(is_in_version_range("4.0", "(Rocky Linux) OpenSSL/3.0.7 ", version_spec))
        self.assertFalse(is_in_version_range("4.0", "(rocky) OpenSSL/3.0.7 ", version_spec))
        self.assertFalse(is_in_version_range("4.0", "(AlmaLinux) OpenSSL/1.1.1k", version_spec))
        self.assertFalse(is_in_version_range("4.0", "(Oracle Linux) OpenSSL/1.1.1k", version_spec))
        self.assertTrue(is_in_version_range("4.0", "", version_spec))


if __name__ == '__main__':
    unittest.main()
