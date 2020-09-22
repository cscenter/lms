from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C, ChoiceItem


class YandexCompilers(DjangoChoices):
    fbc = C("fbc", "Free Basic 1.04")
    c11_x86 = C("c11_x86", "c 11 x32 4.9")
    clang_c11 = C("clang_c11", "Сlang c11 3.8")
    plain_c = C("plain_c", "GNU c 4.9")
    plain_c_x32 = C("plain_c_x32", "GNU c x32 4.9")
    mono_csharp = C("mono_csharp", "Mono C# 5.2.0")
    c11 = C("c11", "GNU c11 4.9")
    clang_cxx11 = C("clang_cxx11", "Clang cxx11 3.8")
    gcc = C("gcc", "GNU c++ 4.9")
    gcc0x = C("gcc0x", "GNU c++ 11 4.9")
    gcc0x_x32 = C("gcc0x_x32", "GNU c++ 11 x32 4.9")
    gcc7_3 = C("gcc7_3", "GNU c++17 7.3")
    dmd = C("dmd", "dmd")
    gdc = C("gdc", "GDC 4.9")
    dcc = C("dcc", "Delphi 2.4.4")
    gc = C("gc", "gc go")
    gccgo = C("gccgo", "gcc go")
    haskell = C("haskell", "Haskell 4.7.1")
    java7 = C("java7", "Oracle Java 7")
    java7_x32 = C("java7_x32", "Oracle Java 7 x32")
    java8 = C("java8", "Oracle Java 8")
    kotlin = C("kotlin", "Kotlin 1.1.50 (JRE 1.8.0)")
    nodejs = C("nodejs", "Node JS 0.10.28")
    ocaml4 = C("ocaml4", "ocaml 4.02.3")
    fpc = C("fpc", "Free pascal 2.4.4")
    perl = C("perl", "Perl 5.14")
    php = C("php", "PHP 5.3.10")
    pypy4 = C("pypy4", "pypy4 ")
    python2_6 = C("python2_6", "Python 2.7")
    python3_4 = C("python3_4", "Python 3.4.3")
    r_core = C("r_core", "R")
    ruby = C("ruby", "Ruby 1.9.3")
    ruby2 = C("ruby2", "ruby 2.2.3")
    rust = C("rust", "rust 1.2")
    scala = C("scala", "Scala 2.9.1")
    bash = C("bash", "GNU bash 4.2.24")
    Others = C("Others", "None")


class CheckingSystemTypes(DjangoChoices):
    YANDEX = ChoiceItem('ya', _("Yandex.Contest"))


class SubmissionStatus(DjangoChoices):
    NEW = ChoiceItem(1, _("New"), css_class='new')
    # SUBMIT_FAIL is set when error occurred during upload to checking system
    SUBMIT_FAIL = ChoiceItem(20, _("Not Submitted"), css_class='failed')
    CHECKING = ChoiceItem(30, _("Checking"), css_class='checking')
    FAILED = ChoiceItem(40, _("Wrong Answer"), css_class='failed')
    PASSED = ChoiceItem(50, _("Correct Answer"), css_class='passed')

    checked_statuses = [FAILED, PASSED]

    @classmethod
    def was_checked(cls, status):
        return status in cls.checked_statuses