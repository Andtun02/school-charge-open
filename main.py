from flask import Flask, render_template,request,jsonify
from pyecharts.charts import Bar, Scatter,Pie
from pyecharts import options as opts
from pyecharts.globals import CurrentConfig, NotebookType
from pyecharts.charts import Page
from datetime import datetime



from api import 完美校园

app = Flask(__name__, static_folder='web', static_url_path='')
api = 完美校园(phone_num='',password='',device_id='')

class server:

    # 使用pyecharts实际上是一个非常不明智的选择，echarts.js 才是正确选择@！@！！
    def render(self):
        # 获得缓存数据
        api.update_from_local() # 其中 power = part_name,[]
        # 处理数据，提取x和y坐标
        _data = [] # 6号公寓，7号公寓
        x_data = [[],[]]  # 6号公寓寝室号，7号公寓寝室号
        y_data = [[],[]]  # 6号公寓寝室电费，7号公寓寝室电费
        index = 0  # 初始化索引值

        for part in api.powers:
            for part_name, rooms in part.items():
                _data.append(part_name)
                for room in rooms:
                    for room_name, room_power in room.items():
                        x_data[index].append(room_name[1:])
                        y_data[index].append(float(room_power))
                index += 1  # 更新索引值

        # 创建散点图
        scatter = (
            Scatter()
            .add_xaxis(x_data[0])
            .add_yaxis(_data[0], y_data[0], symbol="circle", label_opts=opts.LabelOpts(is_show=False))
            .add_yaxis(_data[1], y_data[1], symbol="circle", label_opts=opts.LabelOpts(is_show=False))
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title="各寝室剩余电量散点图",
                    pos_left="center",
                    pos_top="top"
                ),
                legend_opts=opts.LegendOpts(
                    pos_right="right",  # 将图例靠右显示
                    pos_top="top"  # 将图例垂直居中
                )
            )
        )

        # 创建饼图
        me_power = 0
        for i in range(len(x_data[0])):
            if x_data[0][i] == '317':
                me_power = y_data[0][i]
                break

        pie = (
            Pie()
            .add(
                "",
                [
                    ("扫雷组寝室", me_power),
                    ("/", 100 - me_power if me_power <= 100 else 0),
                ],
                radius=["40%", "55%"],  # 设置内外圆的半径比例，即空心饼图
                label_opts=opts.LabelOpts(formatter="{b}: {d}%"),  # 设置标签格式，显示寝室名称和占比
            )
            .set_colors(["#5470c6", "#cccccc"])  # 设置颜色为多色
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title="扫雷组寝室剩余电量",
                    pos_left="center",
                    pos_top="top"
                ),
                legend_opts=opts.LegendOpts(
                    pos_right="right",  # 将图例靠右显示
                    pos_top="top"  # 将图例垂直居中
                )
            )
        )

        # 合并楼层电量
        part_powers = [[], []]
        layer_powers = [[], [], [], [], [], []]

        # 有点头晕。。。
        for i in range(len(y_data)):
            layer_powers = [[], [], [], [], [], []]
            item = y_data[i]
            for j in range(len(item)):
                index = x_data[i][j][:1]
                layer_powers[int(index) - 1].append(item[j])
            part_powers[i] = layer_powers
        part_powers_ = []
        for layers in part_powers:
            layer_sum = []
            for powers in layers:
                layer_sum.append(round(sum(powers),2))
            part_powers_.append(layer_sum)

        layer_x = [f"第{i+1}层" for i in range(len(layer_sum))]
        # 创建柱状图
        bar = (
            Bar()
            .add_xaxis(layer_x)
            .add_yaxis(_data[0],part_powers_[0])
            .add_yaxis(_data[1],part_powers_[1])
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title="各楼层剩余电量总量",
                    pos_left="center",
                    pos_top="top"
                ),
                legend_opts=opts.LegendOpts(
                    pos_right="right",  # 将图例靠右显示
                    pos_top="top"  # 将图例垂直居中
                )
            )
        )


        # 创建页面并添加图表
        page = Page()
        page.add(scatter)
        page.add(pie)
        page.add(bar)
        # 保存图表
        page.render("web/chart.html")

        

    @app.route('/')
    def index():
        with open('web/index.html', 'r', encoding='UTF-8') as f:
            html_content = f.read()
        return html_content
    
    @app.route('/query', methods=['POST'])
    def query():
        data = request.json
        part = data.get('part')
        room = data.get('room')

        # 条件判断
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            if int(room[:1]) > 6 and int(room[:1]) < 1:
                return jsonify({'quantity': 'ERROR', 'currentTime': current_time})
        except:
            return jsonify({'quantity': 'ERROR', 'currentTime': current_time})
        
        # 查询电费
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        res,msg = api.get_power_info(api.query_room(f"{part}{room}"))
        if res:
            return jsonify({'quantity': msg['quantity'] + " 度", 'currentTime': current_time})
        return jsonify({'quantity': msg, 'currentTime': current_time})

if __name__ == '__main__':
    #
    api.init() # 初始化

    web = server()
    web.render() # 绘制图表
    app.run(host='0.0.0.0',port=5050)

