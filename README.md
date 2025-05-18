使用建议：

理想效果：
 * 打开终端/命令行，输入简短命令和参数，既可以查询和修改账号秘密。


安装说明:
1 需要安装 gmssl，执行 pip3 install gmssl 可进行安装


相关设置：
 * shell命令可以执行：设置执行文件搜索路径或将执行文件放入系统执行文件目录
 * shell命令调用python脚本：使用绝对路径


 个人实践：
 1 拷贝python项目文件夹zhmm到/usr/bin目录
 2 在/usr/bin目录下新建zhmm.sh，编辑加入shell命令：
   python3 /usr/bin/zhmm/main.py -i /usr/bin/zhmm/zhmm.gl --openId my_wx_openId $1
   （也可以在此加上pwd）
 3 修改zhmm.sh的权限，如774。
    chmod 774 zhmm.sh
 4 打开终端，输入zhmm.sh -s=a执行。即可打开zhmm并执行查找任务。



# portry 启动应用
poetry run python -m zhmm.main 


# 在Trae中调试，使用Poetry
1. 查看Poetry的虚拟环境路径
    poetry env info
2. 在Trae IDE中选择Poetry虚拟环境
    - 按下 Cmd+Shift+P 打开命令面板
    - 输入并选择 Python: Select Interpreter
    - 在列表中找到并选择Poetry创建的虚拟环境（通常会显示为 Poetry (项目名) 或完整路径），或者输入上面获得的虚拟路径地址

