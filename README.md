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
