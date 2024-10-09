from djchoices import C, ChoiceItem, DjangoChoices

from django.utils.translation import gettext_lazy as _


class YandexCompilers(DjangoChoices):
    fbc = C("fbc", "Free Basic 1.04")
    c11 = C("c11", "GNU c11 4.9")
    c11_x86 = C("c11_x86", "c 11 x32 4.9")
    clang_c11 = C("clang_c11", "Сlang c11 3.8")
    gcc7_c11 = C("gcc7_c11", "GNU GCC 7.3 C11")
    gcc_c17 = C("gcc_c17", "GNU GCC 12.2 C17")
    plain_c = C("plain_c", "GNU c 4.9")
    plain_c_x32 = C("plain_c_x32", "GNU c x32 4.9")
    dotnet5_asp = C("dotnet5_asp", "C# (MS .NET 5.0 + ASP)")
    dotnet6_asp = C("dotnet6_asp", "C# (MS .NET 6.0 + ASP)")
    dotnet_asp = C("dotnet_asp", "C# (MS .Net Core 3.1) + ASP.NET Core")
    mono_csharp = C("mono_csharp", "Mono C# 5.2.0")
    shagraev_csc = C("shagraev_csc", "C# (MS .Net Core 3.1)")
    clang11_cpp20 = C("clang11_cpp20", "Clang11 C++20")
    clang14_cpp20 = C("clang14_cpp20", "Clang 15.0.7 C++20")
    clang_cxx11 = C("clang_cxx11", "Clang cxx11 3.8")
    gcc17_header_footer = C("g++17-header-footer", "g++17-header-footer")
    gcc = C("gcc", "GNU c++ 4.9")
    gcc0x = C("gcc0x", "GNU c++ 11 4.9")
    gcc0x_x32 = C("gcc0x_x32", "GNU c++ 11 x32 4.9")
    gcc5_x64 = C("gcc5_x64", "gcc5_x64")
    gcc7_3 = C("gcc7_3", "GNU c++17 7.3")
    gcc7_o0 = C("gcc7_o0", "GNU C++17 7.3 (-O0)")
    gcc_cpp20 = C("gcc_cpp20", "GNU GCC 12.2 C++20")
    gcc_docker = C("gcc_docker", "GCC 5.4.0 C++14")
    gcc_docker2 = C("gcc_docker2", "GCC C++17")
    gcc_x32 = C("gcc_x32", "GNU c++ x32 4.9")
    gnuc14 = C("gnuc14", "GNU c++ 14 4.9")
    dmd = C("dmd", "dmd")
    gdc = C("gdc", "GDC 4.9")
    dart_2_14 = C("dart_2_14", "Dart 2.19.2")
    gc = C("gc", "gc go")
    gccgo = C("gccgo", "gcc go")
    golang_docker = C("golang_docker", "Golang 1.20.1")
    haskell = C("haskell", "Haskell 7.10.2")
    java7 = C("java7", "Oracle Java 7")
    java7_x32 = C("java7_x32", "Oracle Java 7 x32")
    java8 = C("java8", "Oracle Java 8")
    java8_for_max42 = C("java8_for_max42", "java8_for_max42")
    java8_x32 = C("java8_x32", "java8_x32")
    javac = C("javac", "Oracle Java 8 (48ML)")
    javac_x32 = C("javac_x32", "Oracle Java 7 x 32 (48ML)")
    jdk17 = C("jdk17", "Java 17 (Temurin JDK)")
    jdk19 = C("jdk19", "Java 19 (Temurin JDK)")
    openjdk11_x64 = C("openjdk11_x64", "OpenJDK Java 11")
    openjdk15 = C("openjdk15", "OpenJDK Java 15")
    openjdk6_x32 = C("openjdk6_x32", "OpenJDK Java 6 x32")
    openjdk7_x64 = C("openjdk7_x64", "OpenJDK Java 7 x64")
    node12_mocha = C("node12_mocha", "Mocha (Node.js 12)")
    node8_16 = C("node8_16", "Node JS 8.16")
    nodejs = C("nodejs", "Node JS 0.10.28")
    nodejs692 = C("nodejs692", "Node JS 6.9.2")
    nodejs_16 = C("nodejs_16", "Node.js 16.17.0")
    nodejs_18 = C("nodejs_18", "Node.js 18.7.0")
    nodejs_new = C("nodejs_new", "Node.js 14.15.5")
    kotlin = C("kotlin", "Kotlin 1.1.50 (JRE 1.8.0)")
    kotlin_1_3_50 = C("kotlin_1_3_50", "Kotlin 1.3.50 (JRE 1.8.0)")
    kotlin_1_4_0 = C("kotlin_1_4_0", "Kotlin 1.4.30 (JRE 11)")
    kotlin_1_5_0 = C("kotlin_1_5_0", "Kotlin 1.5.32 (JRE 11)")
    kotlin_1_8_0 = C("kotlin_1_8_0", "Kotlin 1.8.0 (JRE 11)")
    kumir = C("kumir", "kumir 2.1.0-rc9")
    lua_5_4 = C("lua_5_4", "Lua 5.4")
    cpp_make2 = C("cpp-make2", "(make) C++")
    cpp20_make = C("cpp20-make", "(Make) Clang11 C++20")
    cpp20_make_clang14 = C("cpp20-make-clang14", "(Make) Clang 17.0.1 C++20")
    dotnet = C("dotnet", "(Make) C# (MS .Net Core 3.1)")
    dotnet5 = C("dotnet5", "(Make) C# (MS .Net Core 5.0)")
    dotnet6 = C("dotnet6", "(Make) C# (MS .Net Core 6.0)")
    gcc_docker2_make = C("gcc_docker2_make", "(make) GCC C++17")
    gcc_cpp20_make = C("gcc_cpp20_make", "(make) GCC C++20")
    happyfat = C("happyfat", "happyfat")
    idao = C("idao", "(make) idao")
    idao2020 = C("idao2020", "(make) idao2020")
    idao2021 = C("idao2021", "(make) idao2021")
    idao2021_final = C("idao2021_final", "(make) idao2021 final")
    idao2022 = C("idao2022", "(make) idao2022")
    idao2022_final = C("idao2022_final", "(make) idao2022 final")
    ipython3 = C("ipython3", "(make) ipython3")
    ipython3v2 = C("ipython3v2", "(make) ipython3v2")
    javatest = C("javatest", "(make) java test")
    js_blitz = C("js-blitz", "(make) js-blitz")
    lyceum_python_test = C("lyceum_python_test", "(make) Lyceum Python Test")
    make = C("make", "Make")
    make2 = C("make2", "make2")
    mlblitz_python27_numpy = C("mlblitz_python27_numpy", "(make) python2.7+numpy")
    mlblitz_python36_numpy = C("mlblitz_python36_numpy", "(make) python3.5+numpy")
    nodejs_16_make = C("nodejs_16_make", "(make) Node.js 16.17.0")
    nodejs_18_make = C("nodejs_18_make", "(make) Node.js 18.7.0")
    nodejs_make = C("nodejs_make", "(make) nodejs 6.9.2")
    postgres = C("postgres", "(make) postgres")
    python_handbook = C("python-handbook", "(make) python-handbook")
    python_lyceum = C("python-lyceum", "(make) python-lyceum")
    python3_7 = C("python3_7", "(make) Python 3.7.3+modules")
    python_docker_make = C("python_docker_make", "(make) python_docker_make")
    swift_5_3_make = C("swift-5_3_make", "(make) Swift 5.7.3")
    tex = C("tex", "(make) tex")
    tmp_py = C("tmp_py", "(make) tmp_py")
    ycupml2021 = C("ycupml2021", "YCup ML 2021")
    ocaml4 = C("ocaml4", "ocaml 4.02.3")
    clang_objc_arc = C("clang_objc_arc", "Clang objc arc 3.8")
    clang_objc_gc = C("clang_objc_gc", "Сlang objc gc 3.8")
    dcc = C("dcc", "Delphi (FPC 3.2.0)")
    fpc = C("fpc", "Free pascal 2.4.4")
    fpc26 = C("fpc26", "Free Pascal 2.6.2")
    fpc30 = C("fpc30", "Free Pascal 3.2.0")
    pascal_abc = C("pascal_abc", "PascalABC.NET 3.8.3")
    pascalabc = C("pascalabc", "PascalABC.NET 3.5.1")
    test_compiler = C("test_compiler", "test compiler")
    perl = C("perl", "Perl 5.14")
    php = C("php", "PHP 5.3.10")
    php7_3_5 = C("php7_3_5", "PHP 7.3.5")
    php8_1 = C("php8_1", "PHP 8.1")
    pypy3_7_1_0 = C("pypy3_7_1_0", "Python 3.9 (PyPy 7.3.11)")
    pypy4 = C("pypy4", "Python 2.7 (PyPy 4.0.0)")
    python2_6 = C("python2_6", "Python 2.7")
    python3 = C("python3", "Python 3.2")
    python3_4 = C("python3_4", "Python 3.4.3")
    python3_6 = C("python3_6", "Python 3.6")
    python3_7_3 = C("python3_7_3", "Python 3.7.3")
    python3_docker = C("python3_docker", "Python 3.11.2")
    r_core = C("r_core", "R 2.14.1")
    r_modules = C("r_modules", "R 3.6.3 + Modules")
    ruby = C("ruby", "Ruby 1.9.3")
    ruby2 = C("ruby2", "Ruby 2.2.3")
    rust = C("rust", "Rust 1.2")
    rust_1_39_0 = C("rust-1_39_0", "Rust 1.39.0")
    rust154 = C("rust154", "Rust 1.68.0")
    scala = C("scala", "Scala 2.9.1")
    scala_docker = C("scala_docker", "Scala 2.13.4")
    bash = C("bash", "GNU bash 4.2.24")
    data_analysis_handbook = C("data-analysis-handbook", "Python 3.8 (Handbook DS)")
    gnu_cpp_14 = C("gnu c++ 14", "(special) gnu c++ 14")
    hf = C("hf", "(special) hf")
    java17_json = C("java17_json", "OpenJDK 17 + json")
    mlblitz = C("mlblitz", "python3.6+numpy+pandas")
    mlblitz_python26_numpy = C("mlblitz_python26_numpy", "(make) yandexdataschool")
    mono_csharp_5 = C("mono_csharp_5", "(special) Mono C# 5")
    nodejs_make = C("nodejs make", "(make) nodejs (don't use)")
    python3_ml = C("python3-ml", "(make) python3-ml")
    python3_7_ml_modules = C("python3_7_ml_modules", "Python 3.7.3 ML")
    r_ml = C("r-ml", "(make) r-ml")
    screenshots = C("screenshots", "screenshots")
    screenshots_checker = C("screenshots-checker", "screenshots-checker")
    shagraev = C("shagraev", "Python 3.7 + network + requests")
    shagraev_cpp = C("shagraev_cpp", "GNU c++ 11 + net + curl + json")
    shagraev_go = C("shagraev_go", "Golang 1.14.4 + network")
    shagraev_java = C("shagraev_java", "Java 8 + network + json-simple")
    tmp_gcc_coursera = C("tmp_gcc_coursera", "g++17 7.3 controlled")
    sqlite3 = C("sqlite3", "SQLite 3.31.1")
    swift = C("swift", "Swift 4.1.1")
    swift_5_1 = C("swift-5_1", "Swift 5.7.3")
    Others = C("Others", "None")


class CheckingSystemTypes(DjangoChoices):
    YANDEX_CONTEST = ChoiceItem("ya", _("Yandex.Contest"))


class SubmissionStatus(DjangoChoices):
    NEW = ChoiceItem(1, _("New"), css_class="new")
    # SUBMIT_FAIL is set when error occurred during upload to checking system
    SUBMIT_FAIL = ChoiceItem(20, _("Not Submitted"), css_class="failed")
    CHECKING = ChoiceItem(30, _("Checking"), css_class="checking")
    FAILED = ChoiceItem(40, _("Wrong Answer"), css_class="failed")
    PASSED = ChoiceItem(50, _("Correct Answer"), css_class="passed")
