import os
import subprocess
import tempfile
import shutil


def run_evosuite(file_type: str, target: str, classpath: str, output_dir: str) -> bool:
    """
    运行 EvoSuite 生成测试用例

    参数:
        file_type: 文件类型 ('class', 'jar', 'java')
        target: 目标文件路径或类名
        classpath: 类路径
        output_dir: 输出目录
    """
    # 在执行命令前添加
    print(f"[DEBUG] 测试将输出到: {output_dir}")
    if not os.path.exists(output_dir):
        print("[WARNING] 输出目录不存在，尝试创建")
        os.makedirs(output_dir, exist_ok=True)

    java_path = os.path.join("java", "jdk8u452-b09", "bin", "java.exe")
    evosuite_jar = os.path.join("evosuite", "evosuite-1.2.0.jar")

    base_command = [
        java_path,
        f"-Doutput_directory={output_dir}",
        "-jar", evosuite_jar,
        "-projectCP", classpath,
        "-generateTests"
    ]

    try:
        if file_type == 'class':
            # 对于 .class 文件，我们需要提取 FQCN
            fqcn = extract_fqcn_from_class(target)
            if not fqcn:
                print(f"[ERROR] 无法从 {target} 提取完整类名")
                return False

            command = base_command + ["-class", fqcn]

        elif file_type == 'jar':
            # 对于 .jar 文件，我们可以直接使用 jar 文件作为目标
            command = base_command + ["-target", target]

        elif file_type == 'java':
            # 对于 .java 文件，需要先编译
            compiled_dir = compile_java_file(target)
            if not compiled_dir:
                return False

            # 获取主类名（假设文件名与公共类名相同）
            class_name = os.path.splitext(os.path.basename(target))[0]
            command = base_command + [
                "-class", class_name,
                "-projectCP", f"{compiled_dir};{classpath}"
            ]
        else:
            print(f"[ERROR] 不支持的文件类型: {file_type}")
            return False

        print(f"[DEBUG] 执行命令: {' '.join(command)}")
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print("[EvoSuite 输出]:\n", result.stdout)
        return True

    except subprocess.CalledProcessError as e:
        print("[EvoSuite 错误]:\n", e.stderr)
        return False
    finally:
        # 清理临时目录（如果是 Java 文件）
        if file_type == 'java' and 'compiled_dir' in locals():
            shutil.rmtree(compiled_dir, ignore_errors=True)

        # 在执行后添加
    print("[DEBUG] 检查生成的文件:")
    if os.path.exists(output_dir):
        for root, dirs, files in os.walk(output_dir):
            print(f"在 {root} 找到文件: {files}")


def extract_fqcn_from_class(class_file_path: str) -> str:
    """从 .class 文件中提取完整类名"""
    try:
        java_bin = os.path.join("java", "jdk8u452-b09", "bin")
        result = subprocess.run(
            [os.path.join(java_bin, "javap.exe"), "-verbose", class_file_path],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("public class") or line.startswith("class"):
                return line.split(" ")[-1]
    except Exception as e:
        print(f"[ERROR] 提取类名失败: {e}")
    return None


def compile_java_file(java_file_path: str) -> str:
    """编译 .java 文件并返回包含 .class 文件的目录"""
    try:
        # 创建临时目录存放编译结果
        temp_dir = tempfile.mkdtemp()
        java_bin = os.path.join("java", "jdk8u452-b09", "bin")

        # 执行编译
        result = subprocess.run(
            [os.path.join(java_bin, "javac.exe"), "-d", temp_dir, java_file_path],
            capture_output=True, text=True, check=True
        )
        return temp_dir
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] 编译失败: {e.stderr}")
        return None
    except Exception as e:
        print(f"[ERROR] 编译过程中发生错误: {e}")
        return None