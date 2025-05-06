import os
import subprocess
from flask import Flask, request, render_template, redirect, url_for, flash
from evosuite_runner import run_evosuite

app = Flask(__name__)

# 配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
TEST_OUTPUT_FOLDER = os.path.join(BASE_DIR, 'test_outputs')
ALLOWED_EXTENSIONS = {'class', 'jar', 'java'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 限制
app.secret_key = 'your-secret-key-here'  # 用于 flash 消息


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def prepare_upload(file):
    """准备上传的文件，返回保存路径和文件类型"""
    if not file or not allowed_file(file.filename):
        return None, None

    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # 获取文件扩展名
    file_ext = file.filename.rsplit('.', 1)[1].lower()

    # 保存文件
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(save_path)

    return save_path, file_ext


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('没有选择文件')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('没有选择文件')
            return redirect(request.url)

        # 处理上传文件
        file_path, file_type = prepare_upload(file)
        if not file_path:
            flash('不支持的文件类型')
            return redirect(request.url)

        # 根据文件类型处理
        if file_type == 'class':
            # 对于 .class 文件，我们需要提取 FQCN
            java_bin = os.path.join(BASE_DIR, 'java', 'jdk8u452-b09', 'bin')
            fqcn = extract_fqcn_from_class(file_path, java_bin)

            if not fqcn:
                flash('无法从 .class 文件中提取完整类名')
                return redirect(request.url)

            # 构建包路径
            relative_path = fqcn.replace('.', os.sep) + '.class'
            final_path = os.path.join(app.config['UPLOAD_FOLDER'], relative_path)

            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            os.replace(file_path, final_path)

            # 运行 EvoSuite
            success = run_evosuite('class', final_path, app.config['UPLOAD_FOLDER'], TEST_OUTPUT_FOLDER)
            flash(f"测试生成 {'成功' if success else '失败'}，类路径：{fqcn}")

        elif file_type == 'jar':
            # 对于 .jar 文件，直接使用
            success = run_evosuite('jar', file_path, file_path, TEST_OUTPUT_FOLDER)
            flash(f"测试生成 {'成功' if success else '失败'}，JAR 文件：{file.filename}")

        elif file_type == 'java':
            # 对于 .java 文件，需要先编译
            success = run_evosuite('java', file_path, app.config['UPLOAD_FOLDER'], TEST_OUTPUT_FOLDER)
            flash(f"测试生成 {'成功' if success else '失败'}，Java 文件：{file.filename}")

        return redirect(url_for('index'))

    return render_template('index.html')


def extract_fqcn_from_class(class_file_path, java_bin):
    """从 .class 文件中提取完整类名"""
    try:
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


if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(TEST_OUTPUT_FOLDER, exist_ok=True)
    app.run(debug=True)