from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C, ChoiceItem


class YandexCompilers(DjangoChoices):
    fbc = C("fbc", "Free Basic 1.04")
    c11_x86 = C("c11_x86", "c 11 x32 4.9")
    clang_c11 = C("clang_c11", "Сlang c11 3.8")
    gcc7_c11 = C("gcc7_c11", "GNU C11 7.3")
    plain_c = C("plain_c", "GNU c 4.9")
    plain_c_x32 = C("plain_c_x32", "GNU c x32 4.9")
    mono_csharp = C("mono_csharp", "Mono C# 5.2.0")
    c11 = C("c11", "GNU c11 4.9")
    clang_cxx11 = C("clang_cxx11", "Clang cxx11 3.8")
    gcc = C("gcc", "GNU c++ 4.9")
    gcc0x = C("gcc0x", "GNU c++ 11 4.9")
    gnuc14 = C("gnuc14", "GNU c++ 14 4.9")
    gcc0x_x32 = C("gcc0x_x32", "GNU c++ 11 x32 4.9")
    gcc_docker2_make = C("gcc_docker2_make", "GCC C++17 make")
    gcc7_3 = C("gcc7_3", "GNU c++17 7.3")
    dmd = C("dmd", "dmd")
    gdc = C("gdc", "GDC 4.9")
    dcc = C("dcc", "Delphi 2.4.4")
    gc = C("gc", "gc go")
    gccgo = C("gccgo", "gcc go")
    haskell = C("haskell", "Haskell 7.10.2")
    java7 = C("java7", "Oracle Java 7")
    java7_x32 = C("java7_x32", "Oracle Java 7 x32")
    java8 = C("java8", "Oracle Java 8")
    kotlin = C("kotlin", "Kotlin 1.1.50 (JRE 1.8.0)")
    kotlin_1_3_50 = C("kotlin_1_3_50", "Kotlin 1.3.50 (JRE 1.8.0)")
    nodejs = C("nodejs", "Node JS 0.10.28")
    ocaml4 = C("ocaml4", "ocaml 4.02.3")
    fpc30 = C("fpc30", "Free Pascal 3.0.0")
    pascalabc = C("pascalabc", "PascalABC.NET 3.5.1")
    perl = C("perl", "Perl 5.14")
    php = C("php", "PHP 5.3.10")
    php7_3_5 = C("php7_3_5", "PHP 7.3.5")
    pypy4 = C("pypy4", "pypy4 ")
    python2_6 = C("python2_6", "Python 2.7")
    python3_7_3 = C("python3_7_3", "Python 3.7.3")
    r_core = C("r_core", "R")
    ruby = C("ruby", "Ruby 1.9.3")
    ruby2 = C("ruby2", "ruby 2.2.3")
    rust = C("rust", "rust 1.2")
    rust_1_39_0 = C("rust-1_39_0", "Rust 1.39.0")
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
