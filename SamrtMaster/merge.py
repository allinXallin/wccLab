#!/data/wwwroot/python363
# coding=utf-8


import os,random,math,json,requests,time,cv2
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from flask import Flask, request, Response, send_file, make_response
from io import BytesIO
from flask_cors import CORS
#import matplotlib.pyplot as plt





# 风格模板类
class StyleLayout:
    # 静态字段tmpl_count，用来统计使用的模板总数
    tmpl_count = 0

    def __init__(self, background,foreground,title, sub_title, content, logo, photo):
        self.background = background
        self.foreground = foreground
        self.title = title
        self.sub_title = sub_title
        self.content = content
        self.logo = logo
        self.photo = photo


# 文本类
class TextConstraint:
    def __init__(self, left_top, right_bottom, min_size, max_size, align, precent, font_family,color):
        self.left_top = left_top
        self.right_bottom = right_bottom
        self.min_size = min_size
        self.max_size = max_size
        self.align = align
        self.precent = precent
        self.font_family = font_family
        self.color = color

    # 获取约束框的左上角和右下角坐标值，绝对值
    def get_rect_space(self, WIDTH, HEIGHT):
        left_top = self.left_top.strip().split("|")
        right_bottom = self.right_bottom.strip().split("|")
        return float(left_top[0]) / 100 * WIDTH, float(left_top[1]) / 100 * HEIGHT, float(
            right_bottom[0]) / 100 * WIDTH, float(right_bottom[1]) / 100 * HEIGHT


# # 副标题元素类
# class SubTitle:
#     def __init__(self, left_top, right_bottom, min_size, max_size,align):
#         self.left_top = left_top
#         self.right_bottom = right_bottom
#         self.min_size = min_size
#         self.max_size = max_size
#         self.align = align
#
#
# # 文字内容元素类
# class Content:
#     def __init__(self, left_top, right_bottom, min_size, max_size, align):
#         self.left_top = left_top
#         self.right_bottom = right_bottom
#         self.min_size = min_size
#         self.max_size = max_size
#         self.align = align


# LOGO元素类
#####    是否还需要指定放置方式，如是缩放至box的相同大小，还是说按原始比例裁剪
class Logo:
    def __init__(self, left_top, right_bottom, align, precent):
        self.left_top = left_top
        self.right_bottom = right_bottom
        self.align = align
        self.precent = precent

    # 获取约束框的左上角和右下角坐标值，绝对值
    def get_rect_space(self, WIDTH, HEIGHT):
        left_top = self.left_top.strip().split("|")
        right_bottom = self.right_bottom.strip().split("|")
        return float(left_top[0]) / 100 * WIDTH, float(left_top[1]) / 100 * HEIGHT, float(
            right_bottom[0]) / 100 * WIDTH, float(right_bottom[1]) / 100 * HEIGHT



# 照片元素类
class Photo:
    def __init__(self, left_top, right_bottom, right_top, left_bottom, align, precent, geometry,face_lefttop,face_rightbottom):
        self.left_top = left_top
        self.right_bottom = right_bottom
        self.right_top = right_top
        self.left_bottom = left_bottom
        self.align = align
        self.precent = precent
        self.geometry = geometry
        self.face_lefttop = face_lefttop
        self.face_rightbottom = face_rightbottom

    # 判断是否是长方形
    def is_rect(self):
        left_top = self.left_top.strip().split("|")
        right_bottom = self.right_bottom.strip().split("|")
        right_top = self.right_top.strip().split("|")
        left_bottom = self.left_bottom.strip().split("|")
        # if float(left_top[0]) == float(left_bottom[0]) and float(left_top[1]) == float(right_top[1]) and float(right_bottom[0]) == float(right_top[0]) and float(right_bottom[1]) == float(left_bottom[1]):
        if left_top[0] == left_bottom[0] and left_top[1] == right_top[1] and right_bottom[0] == right_top[0] and \
                        right_bottom[1] == left_bottom[1]:
            return True
        else:
            return False

    # 获取约束框的左上角和右下角坐标值，绝对值
    def get_rect_space(self, WIDTH, HEIGHT):
        left_top = self.left_top.strip().split("|")
        right_bottom = self.right_bottom.strip().split("|")
        return float(left_top[0]) / 100 * WIDTH, float(left_top[1]) / 100 * HEIGHT, float(
            right_bottom[0]) / 100 * WIDTH, float(right_bottom[1]) / 100 * HEIGHT

    # 获取非长方形的四边形的四个点的坐标值，绝对值，顺时针返回
    def get_quadrilateral_space(self, WIDTH, HEIGHT):
        left_top = self.left_top.strip().split("|")
        right_bottom = self.right_bottom.strip().split("|")
        right_top = self.right_top.strip().split("|")
        left_bottom = self.left_bottom.strip().split("|")
        return float(left_top[0]) / 100 * WIDTH, float(left_top[1]) / 100 * HEIGHT, float(
            right_top[0]) / 100 * WIDTH, float(right_top[1]) / 100 * HEIGHT, float(
            right_bottom[0]) / 100 * WIDTH, float(right_bottom[1]) / 100 * HEIGHT, float(
            left_bottom[0]) / 100 * WIDTH, float(left_bottom[1]) / 100 * HEIGHT

    # 获取人脸约束框的左上角和右下角的坐标值，绝对值
    def get_face_space(self, WIDTH, HEIGHT):
        face_lefttop = self.face_lefttop.strip().split("|")
        face_rightbottom = self.face_rightbottom.strip().split("|")
        return float(face_lefttop[0]) / 100 * WIDTH, float(face_lefttop[1]) / 100 * HEIGHT, float(
            face_rightbottom[0]) / 100 * WIDTH, float(face_rightbottom[1]) / 100 * HEIGHT


# 色彩组类
class ColorGroup:
    def __init__(self, master, secondary, intersperse):
        self.master = master
        self.secondary = secondary
        self.intersperse = intersperse



# #添加标题
# # srcImg：原图片     title：用户提交的标题文字    cntX标题约束空间中心点X坐标（%），cntY标题约束空间中心点Y坐标（%），
# # width标题约束空间宽度（%），height标题约束空间高度（%），
# def addTitle(srcImg,title,cntX,cntY,width,height):
#     #计算背景图片尺寸
#     srcImgSize = srcImg.size
#     print('%d  %d' % (srcImgSize[0], srcImgSize[1]))
#     print (float(float(cntX) - float(width) / 2))
#     leftTopX=srcImgSize[0]*float(float(cntX)-float(width)/2)/100
#     leftTopY=srcImgSize[1]*float(float(cntY)-float(height)/2)/100
#
#     # font = ImageFont.new('RGB',(width,height),(255,255,255))
#     # 设置字体
#     font = ImageFont.truetype('webFonts/wygdmc.otf', random.randint(100, 120))
#     draw = ImageDraw.Draw(srcImg)
#     draw.text((leftTopX, leftTopY), title, rndColor(), font)
#
#
#
# #添加副标题
# def addSubTitle(srcImg,subTitle,cntX,cntY,width,height):
#     srcImgSize = srcImg.size
#     print('%d  %d' % (srcImgSize[0], srcImgSize[1]))
#     print (float(float(cntX) - float(width) / 2))
#     leftTopX=srcImgSize[0]*float(float(cntX)-float(width)/2)/100
#     leftTopY=srcImgSize[1]*float(float(cntY)-float(height)/2)/100
#
#     # font = ImageFont.new('RGB',(width,height),(255,255,255))
#     # 设置字体
#     font = ImageFont.truetype('webFonts/zlyyt.otf', random.randint(80, 100))
#     draw = ImageDraw.Draw(srcImg)
#
#     draw.text((leftTopX, leftTopY), subTitle, rndColor(), font)
#
# #添加正文内容
# def addContent(srcImg,content,cntX,cntY,width,height):
#     srcImgSize = srcImg.size
#     print('%d  %d' % (srcImgSize[0], srcImgSize[1]))
#     print (float(float(cntX) - float(width) / 2))
#     leftTopX=srcImgSize[0]*float(float(cntX)-float(width)/2)/100
#     leftTopY=srcImgSize[1]*float(float(cntY)-float(height)/2)/100
#
#     # font = ImageFont.new('RGB',(width,height),(255,255,255))
#     # 设置字体
#     font = ImageFont.truetype('webFonts/kamct.ttf', random.randint(30, 50))
#     draw = ImageDraw.Draw(srcImg)
#
#     draw.text((leftTopX, leftTopY), content, rndColor(), font)
#
#
# #添加油站logo
# def addLogo(srcImg,logo,cntX,cntY,width,height):
#
#     """"
#     srcImgSize = srcImg.size
#     print('%d  %d' % (srcImgSize[0], srcImgSize[1]))
#     print (float(float(cntX) - float(width) / 2))
#     leftTopX =srcImgSize[0]*float(float(cntX)-float(width)/2)/100
#     leftTopY =srcImgSize[1]*float(float(cntY)-float(height)/2)/100
#
#     srcImg.
# """
#     print ("adsf")
#
#
# #添加用户上传的图
# def addImage():
#     print("add image successful！")
#
#
# #画一张海报，包括title、subtitle、content、logo、image
# def  drawPoster(template,userinput):
#     # 读取背景图片  PIL读取图片方式
#     # background = Image.open('background/happy1.jpg')
#
#     cvim = cv.imread("background/happy1.jpg", cv.COLOR_BGR2RGB)
#     background = Image.fromarray(cvim)
#
#     #在图片上绘制各个信息
#     addTitle(background,userinput[2],template[2],template[3],template[4],template[5])
#     addSubTitle(background,userinput[3],template[6],template[7],template[8],template[9])
#     addContent(background,userinput[4],template[10],template[11],template[12],template[13])
#     addLogo(background,userinput[5],template[14],template[15],template[16],template[17])
#     addImage()
#
#     im = np.array(background)
#     cv.imwrite('outputPosters/user'+userinput[0]+'_'+template[0]+'.jpg', im)
#     cv.imshow("name window", im)
#     cv.waitKey(0)  # 等待下一个操作，才会消失，释放内存
#     cv.destroyAllWindows()


# 生成多张可选海报
def produce_posters(json_data):
    """以下是之前本地测试的版本================================================
    #####
    # 解析用户上传元素，并加载到程序中，每个用户信息保存到一个字典内
    # 打开用户元素txt文件,   注意：用utf-8会出现‘\ufeff’
    txtFile = open(user_url + "/" + user_url + ".txt", 'r', encoding='utf-8-sig')
    lines = txtFile.readlines()
    # 用户字典，保存用户上传的元素，图片以url形式给出
    userInfoDict={}
    for line in lines:
        lineData  = line.strip().split(":",1)
        if lineData[0] == u'风格':
            userInfoDict['style']=lineData[1]
        if lineData[0] == u'标题':
            userInfoDict['title']=lineData[1]
        if lineData[0] == u'辅助文字':
            userInfoDict['subTitle'] = lineData[1]
        if lineData[0] == u'说明文字':
            userInfoDict['content'] = lineData[1]
    userInfoDict['logo'] = user_url+"/"+'icon.png'    # logo信息不在txt文件中，单独处理
    userInfoDict['photo'] = user_url+'/'+'photo.png'  # photo信息不在txt文件中，单独处理
    =========================================================================="""

    # 解析用户上传元素，并加载到程序中，每个用户信息保存到一个字典内
    task_info = {}
    ALGORITHM_UPGRADDE = json_data.get('AlgorithmUpgrade')
    task_info['uid'] = json_data.get('user_id')
    task_info['task_id'] = json_data.get('taskid')
    task_info['style'] = json_data.get('style_name')
    task_info['title'] = json_data.get('title')
    task_info['subtitle'] = json_data.get('subtitle')
    task_info['content'] = json_data.get('content')
    task_info['logo'] = json_data.get('logo')
    task_info['photo'] = json_data.get('photo')


    # 创建好海报存放路径，海报文件存放路径path：[uid]/[tsakid]
    path = 'outputPosters/' + str(task_info['uid']) + '/' + str(task_info['task_id'])
    if not os.path.exists(path):
        os.makedirs(path)

    # 获取用户选择的风格类型，并在模板库中选择前N个模板进行制作
    style = task_info['style']
    layout_id, color_group_id, fonts_name = get_layout_id_by_style(style)

    # 根据布局ID从layout.xml文件中选择，并把模板约束信息保存到style_layouts中
    style_layouts = get_layouts_by_id(layout_id)

    # 根据色彩组ID从色彩库文件color.xml选出色彩组并保存到style_colors
    style_colors = get_colors_by_id(color_group_id)

    RECOMMEND_NUM = 4  # 返回给用户的推荐海报数为5，可调整
    count = 0  # 统计制作海报的个数
    couple = []  # 记录tyle_layouts、style_colors的组合，避免重复
    posters_result = {}  # 制作好的海报，以任务为单位，里面包含多个psd格式信息
    posters_result['taskid'] = json_data.get('taskid')


    # 若tyle_layouts、style_colors组合总数小于recommend_num，则取小的为主
    for k in range(
            RECOMMEND_NUM if len(style_layouts) * len(style_colors) > RECOMMEND_NUM else len(style_layouts) * len(
                    style_colors)):
        # 随机从style_layouts、style_colors两个列表中抽取一对布局和色彩组合，但保证不能有重复
        i, j = get_new_couple_index(len(style_layouts) - 1, len(style_colors) - 1, couple)
        couple.append([i, j])
        # 开始制作海报,输入参数1：海报模板约束样式；参数2：用户上传元素。返回值：json格式
        z = random.randint(0, len(fonts_name) - 1)
        poster = draw_a_poster(task_info, style_layouts[i], style_colors[j], fonts_name[z], path)  # path图层信息存放路径
        # 计算海报存放路径path下文件数num，则此次制作出来的海报的键即为该海报psd生成树信息的txt文件所在目录
        num = len([x for x in os.listdir(path)])
        posters_result[path + "/p_" + str(num) +"/p_"+str(num)+".txt"] = poster
        #poster = json.dumps(poster, ensure_ascii=False)
    return posters_result


# #===========================本地测试版=========================
# # 制作好海报后，以POST方式发送数据回后端
# def send_posters_info(posters_result):
#     URL = 'http://172.16.0.200/api/v1/psdinfo'  # web后端地址
#     # 待返回给后端的信息，post给后端
#     post_data = {}
#     post_data['task_id'] = posters_result['taskid']
#     post_data['AlgorithmUpgrade'] = 1
#     posters_result.pop('taskid')
#     k = 1 # 海报计数器
#     pre_imgurl = "http://172.16.0.50:5050/image/?imgurl="
#     #先移除posters_result字典中taskid，其余则是海报相关的信息
#     files={}
#     for key,value in posters_result.items():
#         post_data['preview_url_' + str(k)] = pre_imgurl + value['name']
#         files['psdinfo_' + str(k)] = open(key, 'rb')
#         k=k+1
#     print(post_data)
#     #以post方式发送给web后端
#     try:
#         #post_data = json.dumps(post_data)
#         response = requests.post(URL,post_data,files=files)
#         #response = json.loads(response)
#         print(response.text)
#     except Exception as e:
#         # 若海报信息post传递失败，则将海报放到制作好的海报队列中
#         #=======================================================
#
#         print(str(e))
#
#     # 使用requests发送POST请求。   一个http请求 = 请求行 + 请求报头 + 消息主体
#     # # 方式一：application/x-www-form-urlencoded      form表单形式提交数据（需构造一个字典）
#     # URL = 'http://120.78.10.209/api/v1/psdinfo'
#     # data = {'preimg_url_1':'http://172.16.0.70:5050/image/?imgurl=background/happy1.jpg','preimg_url_2':'http://172.16.0.70:5050/image/?imgurl=background/happy2.jpg'}
#     # req = requests.post(URL,data=data)
#     # print(req.json())
#
#     # # 方式二：application/json    以json串提交数据
#     # URL = 'http://120.78.10.209/api/v1/psdinfo'
#     # data = json.dumps({'key1':'value', 'key2':'value2'})
#     # req = requests.post(URL,data=data)
#     # print(req.text)
#
#     # # 方式三；multipart/form-data     用来上传文件
#     # URL = 'http://120.78.10.209/api/v1/psdinfo'
#     # file = {'file': open('outputPosters/1/1/p_1/p_1.txt', 'rb')}
#     # req = requests.post(URL,files=file)
#     # print(req.text)




#======================服务器部署版============================
# 制作好海报后，以POST方式发送数据回后端
def send_posters_info(posters_result):
    URL = 'http://wx.weicheche.cn/wxposters/api/v1/psdinfo'
    post_data = {}
    post_data['task_id'] = posters_result['taskid']
    post_data['AlgorithmUpgrade'] = 1
    posters_result.pop('taskid')
    k = 1
    pre_imgurl = "http://120.78.10.209:5050/image/?imgurl="
    files={}
    for key,value in posters_result.items():
        post_data['preview_url_' + str(k)] = pre_imgurl + value['name']

        files['psdinfo_' + str(k)] = open(key, 'rb')
        k=k+1
    print(post_data)
    try:
        response = requests.post(URL,post_data,files=files)
        #print(response.text)
    except Exception as e:
        print(str(e))


# 解析style.xml文件，通过style找到匹配的template_ID、color_group_ID、font_family
def get_layout_id_by_style(input_style):
    try:
        etree = ET.parse('xml/style.xml')
        root = etree.getroot()
    except Exception as e:
        print(str(e))
        print('Error:cannot parse file : xml/style.xml.')
        return -1

    layout_IDs = []
    color_group_IDs = []
    font_familys = []
    styles = root.findall('style')
    for eachstyle in styles:
        if eachstyle.find('name').text == input_style:
            # 注意要判断子元素是否为空，为空的话提醒为模板增加元素
            for child in eachstyle.getchildren():
                if child.tag == "layout_IDs":
                    layout_IDs = child.text.strip().split('|')
                if child.tag == "color_group_IDs":
                    color_group_IDs = child.text.strip().split('|')
                if child.tag == "font_family":
                    font_familys = child.text.strip().split('|')
    return layout_IDs, color_group_IDs, font_familys


# 解析layout.xml文件，通过layout的id找到title、sub_title、content、logo和photo的约束空间描述
def get_layouts_by_id(layout_IDs):
    try:
        etree = ET.parse("xml/layout.xml")
        root = etree.getroot()
    except Exception as e:
        print(str(e))
        print("'Error:cannot parse file : xml/layout.xml.'")
    # 用style_layouts存储符合风格类型的布局样式
    style_layouts = []
    layouts = root.findall('layout')
    for index in layout_IDs:
        for each_layout in layouts:
            if each_layout.get('id') == index:
                for child in each_layout.getchildren():
                    if child.tag == "background":
                        background = child.text
                    if child.tag == "foreground":
                        foreground = child.text
                    if child.tag == "title":
                        left_top, right_bottom, min_size, max_size, align,precent,font_family,color = get_text_element_by_child(child)
                        title = TextConstraint(left_top, right_bottom, min_size, max_size, align,precent,font_family,color)
                    if child.tag == "sub_title":
                        left_top, right_bottom, min_size, max_size, align,precent,font_family,color = get_text_element_by_child(child)
                        sub_title = TextConstraint(left_top, right_bottom, min_size, max_size, align,precent,font_family,color)
                    if child.tag == "content":
                        left_top, right_bottom, min_size, max_size, align,precent,font_family,color = get_text_element_by_child(child)
                        content = TextConstraint(left_top, right_bottom, min_size, max_size, align,precent,font_family,color)
                    if child.tag == "logo":
                        left_top, right_bottom, align,precent = get_img_element_by_child(child)
                        logo = Logo(left_top, right_bottom, align,precent)
                    if child.tag == "photo":
                        left_top, right_bottom, right_top, left_bottom, align, precent, geometry,face_lefttop,face_rightbottom = get_img_element_by_child(
                            child)
                        photo = Photo(left_top, right_bottom, right_top, left_bottom, align, precent, geometry,face_lefttop,face_rightbottom)
                # 生成一个模板实例，并添加到模板列表中
                tmpl_impl = StyleLayout(background,foreground, title, sub_title, content, logo, photo)
                style_layouts.append(tmpl_impl)
    return style_layouts


# 在xml文件中从子元素中找文本类子元素
def get_text_element_by_child(child):
    font = None
    color = None
    #注意：不能把上面两个变量font color同时放在for循环里面，否则肯定有一个会出现问题
    for cdcd in child.getchildren():
        if cdcd.tag == "point_lefttop":
            left_top = cdcd.text.strip()
        if cdcd.tag == "point_rightbottom":
            right_bottom = cdcd.text.strip()
        if cdcd.tag == "font_size_min":
            min_size = cdcd.text.strip()
        if cdcd.tag == "font_size_max":
            max_size = cdcd.text.strip()
        if cdcd.tag == "align":
            align = cdcd.text.strip()
        if cdcd.tag == "precent":
            precent = cdcd.text.strip()
        # 局部特殊字体，有的文本约束框可能没有font设置
        if cdcd.tag == "font_family":
            font = cdcd.text.strip()
        # 局部特殊颜色，有的文本约束框可能没有color设置
        if cdcd.tag == "color":
            color = cdcd.text.strip()
    return left_top, right_bottom, min_size, max_size, align, precent,font,color


# 在xml文件中从子元素中找图像类子元素
def get_img_element_by_child(child):
    if child.tag == "logo":
        for cdcd in child.getchildren():
            if cdcd.tag == "point_lefttop":
                left_top = cdcd.text.strip()
            if cdcd.tag == "point_rightbottom":
                right_bottom = cdcd.text.strip()
            if cdcd.tag == "align":
                align = cdcd.text.strip()
            if cdcd.tag == "precent":
                precent = cdcd.text.strip()
        return left_top, right_bottom, align,precent
    elif child.tag == "photo":
        face_lefttop = None
        face_rightbottom = None
        for cdcd in child.getchildren():
            if cdcd.tag == "point_lefttop":
                left_top = cdcd.text.strip()
            if cdcd.tag == "point_rightbottom":
                right_bottom = cdcd.text.strip()
            if cdcd.tag == "point_righttop":
                right_top = cdcd.text.strip()
            if cdcd.tag == "point_leftbottom":
                left_bottom = cdcd.text.strip()
            if cdcd.tag == "align":
                align = cdcd.text.strip()
            if cdcd.tag == "precent":
                precent = cdcd.text.strip()
            if cdcd.tag == "geometry":
                geometry = cdcd.text.strip()
            if cdcd.tag == 'face_lefttop':
                face_lefttop = cdcd.text.strip()
            if cdcd.tag == 'face_rightbottom':
                face_rightbottom = cdcd.text.strip()
        return left_top, right_bottom, right_top, left_bottom, align, precent, geometry,face_lefttop,face_rightbottom


# 解析color.xml文件，通过colorGroup的id找到符合风格的色彩组
def get_colors_by_id(color_group_id):
    try:
        etree = ET.parse("xml/color.xml")
        root = etree.getroot()
    except Exception as e:
        print(str(e))
        print("Error:cannot parse xml/color.xml !")
    # 用style_colors存储符合风格类型的色彩库
    style_colors = []
    groups = root.findall('color_group')
    for id in color_group_id:
        for cg in groups:
            if cg.get('id') == id:
                for child in cg.getchildren():
                    if child.tag == 'master':
                        master = child.text
                    if child.tag == 'secondary':
                        secondary = child.text
                    if child.tag == 'intersperse':
                        intersperse = child.text
                color_group = ColorGroup(master, secondary, intersperse)
                style_colors.append(color_group)
    return style_colors


# 随机从两个列表中抽取一对索引，并保证couple中元素唯一性
def get_new_couple_index(len1, len2, couple):
    i = random.randint(0, len1)
    j = random.randint(0, len2)
    while [i, j] in couple:
        i = random.randint(0, len1)
        j = random.randint(0, len2)
    return i, j


# 创建画布并开始绘制画报不同图层
def draw_a_poster(userInfoDict, style_layout, style_color, font, path):
    psd_layers = {}  # 海报格式信息，psd图层树

    # 计算海报存放路径path下文件数num，该海报文件名为'num+1'
    num = len([x for x in os.listdir(path)])
    poster_path = path + '/p_' + str(num + 1)
    os.makedirs(poster_path)
    psd_layers['name'] = poster_path + "/p_" + str(num + 1) + '.png'

    # 定义海报的整个尺寸
    # WIDTH = 1656
    # HEIGHT = 2696
    WIDTH = 828
    HEIGHT = 1348
    # 在海报json里面添加宽高信息
    psd_layers['width'] = WIDTH
    psd_layers['height'] = HEIGHT

    # 声明background和layers，以备后期添加
    psd_layers['background'] = {}
    psd_layers['layers'] = []

    # 若有预设背景图，则用预设背景图否则根据颜色组绘制单一颜色
    if style_layout.background is not None:
        background = Image.open(style_layout.background)
    else:
        background = Image.new("RGB", (WIDTH, HEIGHT), str(style_color.master))
    # 将绘制好的背景保存到对应目录下
    background.save(poster_path + '/bg.png')

    img = background

    # 制作类似json格式的图层信息，并添加到psd_layers中的'layers'列表中去
    json_background = {}
    psd_layers['background']['name'] = "背景图"
    psd_layers['background']['image'] = poster_path + '/bg.png'
    psd_layers['background']['opacity'] = 1

    # 绘制photo   注：photo可以为空    注：参数shape表示photo容器的形状：Q-四边形 T-三角形 C-圆形
    if userInfoDict['photo'] is not None:
        photo_png, psd_layers = draw_photo(img, psd_layers, userInfoDict["photo"], style_layout.photo, WIDTH, HEIGHT, 'Q')
        photo_png.save(poster_path + '/photo.png')
        psd_layers['layers'][-1]['image'] = poster_path + '/photo.png'


    # 若有预设【前景图】，则用预设前景图
    if style_layout.foreground is not None:
        fgs = style_layout.foreground.strip().split('|')
        index = random.randint(0,len(fgs)-1)
        foreground = Image.open('foreground/' + fgs[index])
        # 绘制前景图到img上    注意：此时前景色跟图片的分辨率一样，可直接paste，后期可能不一样
        img.paste(foreground,(0,0,WIDTH,HEIGHT),mask=foreground)
        # 将前景图保存到对应目录下
        foreground.save(poster_path + '/fg.png')

        # 制作类似json格式的图层信息，并添加到psd_layers中的'layers'列表中去
        json_layer = {}
        number = len(psd_layers['layers']) + 1  # 图层id
        json_layer['number'] = number
        json_layer['name'] = "前景图"
        json_layer['left'] = 0
        json_layer['top'] = 0
        json_layer['width'] = WIDTH
        json_layer['height'] = HEIGHT
        json_layer['opacity'] = 1
        json_layer['image'] = poster_path + '/fg.png'
        # 将制作好的文本图层添加进psd_layers的layers中去
        psd_layers['layers'].append(json_layer)


    # 绘制logo     注：logo可以为空 注：①暂时logo只能绘制在长方形容器中；②参数mode表示是否允许裁剪，logo不允许裁剪，photo允许裁剪
    if userInfoDict['logo'] is not None:
        logo_png, psd_layers = draw_img_in_rect(img, psd_layers, userInfoDict["logo"], style_layout.logo, WIDTH,
                                                HEIGHT, False)
        logo_png.save(poster_path + '/logo.png')
        psd_layers['layers'][-1]['image'] = poster_path + '/logo.png'

    # 绘制Title，不可换行；同时生成单独的图层返回     注：标题内容不能为空，且在前端已经限制校验
    title_png, psd_layers = draw_title(img, psd_layers, userInfoDict["title"], style_layout.title,
                                      style_color.secondary, "webFonts/" + font, False, poster_path)
    title_png.save(poster_path + '/title.png')
    psd_layers['layers'][-1]['image'] = poster_path + '/title.png'

    # 绘制subTitle，不可换行；同时生成单独的图层返回   注：副标题可以为空
    if userInfoDict['subtitle'] is not None:
        subtitle_png, psd_layers = draw_title(img, psd_layers, userInfoDict["subtitle"], style_layout.sub_title,
                                             style_color.intersperse, "sysFonts/simhei.ttf", False,
                                             poster_path)
        subtitle_png.save(poster_path + '/subtitle.png')
        psd_layers['layers'][-1]['image'] = poster_path + '/subtitle.png'

    #
    # # 绘制subTitle，不可换行；同时生成单独的图层返回   注：副标题可以为空
    # if userInfoDict['subtitle'] is not None:
    #     subtitle_png, psd_layers = draw_text(img, psd_layers, userInfoDict["subtitle"], style_layout.sub_title,
    #                                          style_color.intersperse, "sysFonts/simhei.ttf", False,
    #                                          poster_path)
    #     subtitle_png.save(poster_path + '/subtitle.png')
    #     psd_layers['layers'][-1]['image'] = poster_path + '/subtitle.png'

    # 绘制content，可换行；同时生成单独的图层返回   注：content内容可以为空
    if userInfoDict['content'] is not None:
        if int(style_layout.content.precent) != 0 :
            content_png, psd_layers = draw_text(img, psd_layers, userInfoDict["content"], style_layout.content,
                                                style_color.intersperse, "sysFonts/simhei.ttf", True,
                                                poster_path)
            content_png.save(poster_path + '/content.png')
            psd_layers['layers'][-1]['image'] = poster_path + '/subtitle.png'


    img.save(poster_path + '/' + 'p_' + str(num + 1) + '.png')
    layers_txt = poster_path + '/' + 'p_' + str(num + 1) + '.txt'
    with open(layers_txt, 'w', encoding='utf-8') as txt_file:
        json.dump(psd_layers, txt_file, ensure_ascii=False)
        txt_file.close()
    return psd_layers


# 绘制文本信息（title、subtitle、content）至背景图片上，同时生成单独的图层返回；最后一个参数表示是否可换行
def draw_title(img, psd_layers, text, constraint, color, font, multiline_or_not, path):
    # 根据长宽计算左上角和右下角的绝对位置
    left_top_x, left_top_y, right_bottom_x, right_bottom_y = constraint.get_rect_space(psd_layers['width'],
                                                                                       psd_layers['height'])
    # 按比例缩放约束空间
    PERCENT_TEXT_SPACE = float(constraint.precent)/100
    left_top_x, left_top_y, right_bottom_x, right_bottom_y = shrink_rect(left_top_x, left_top_y, right_bottom_x,
                                                                         right_bottom_y, PERCENT_TEXT_SPACE)
    # 文字绘制的边界：left，top，width，height
    box_in_box = ()
    # 添加到json里面的字体尺寸
    actual_size = 0

    # 设置字体，若有特殊字体要求，则用特殊字体
    if constraint.font_family is not None:
        font = "webFonts/" + constraint.font_family
        #print(font)

    # 设置颜色，若有特殊颜色要求，则用颜色字体
    if constraint.color is not None:
        color = constraint.color

    # 在主背景图img上和图层图img_layer上都进行绘制
    draw_img = ImageDraw.Draw(img)
    layer_png = Image.new(mode='RGBA', size=(right_bottom_x - left_top_x, right_bottom_y - left_top_y))
    draw_layer = ImageDraw.Draw(layer_png)
    if multiline_or_not is False:  # 标题和副标题不可换行
        for now_size in range(int(constraint.max_size), int(constraint.min_size), -2):
            ft = ImageFont.truetype(font, now_size)
            w, h = ft.getsize(text)
            # 由于相同字号的不同字体的长宽都有所不同，所以要先判断整个字符串的长宽，若超出约束空间则减小字号
            if w < (right_bottom_x - left_top_x) and h < (right_bottom_y - left_top_y):
                # 将最适合的字体大小保存到actual_size，供生成json使用
                actual_size = now_size
                # 根据要求的对齐方式进行绘制，left、center、right
                if constraint.align == "left":  # 文本左对齐
                    draw_img.text((left_top_x, left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2), text,
                                  fill=color, font=ft)
                    draw_layer.text((0, (right_bottom_y - left_top_y) / 2 - h / 2), text, fill=color, font=ft)
                    box_in_box = (left_top_x, left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2, left_top_x+w, h + left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2)
                elif constraint.align == "center":  # 文本中间对齐
                    draw_img.text((left_top_x + (right_bottom_x - left_top_x) / 2 - w / 2,
                                   left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2), text, fill=color, font=ft)
                    draw_layer.text(
                        ((right_bottom_x - left_top_x) / 2 - w / 2, (right_bottom_y - left_top_y) / 2 - h / 2), text,
                        fill=color, font=ft)
                    box_in_box = (left_top_x + (right_bottom_x - left_top_x) / 2 - w / 2,
                                  left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2, w+left_top_x + (right_bottom_x - left_top_x) / 2 - w / 2, h+left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2)
                elif constraint.align == "right":  # 文本右对齐
                    draw_img.text((right_bottom_x - w, left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2), text,
                                  fill=color, font=ft)
                    draw_layer.text((right_bottom_x - w - left_top_x, (right_bottom_y - left_top_y) / 2 - h / 2), text,
                                    fill=color, font=ft)
                    box_in_box = (right_bottom_x - w, left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2, right_bottom_x, h +left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2)
                else :  # 文本左下角对齐
                    draw_img.text((left_top_x, left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2), text,
                                  fill=color, font=ft)
                    draw_layer.text((0, (right_bottom_y - left_top_y) / 2 - h / 2), text, fill=color, font=ft)
                    box_in_box = (left_top_x, left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2, left_top_x + w,
                                  h + left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2)
                break
    else:  # content可换行
        for now_size in range(int(constraint.max_size), int(constraint.min_size), -1):
            ft = ImageFont.truetype(font, now_size)
            w, h = ft.getsize(text)
            # 内容文字可换行，若行数不超出约束空间，则可绘制，否则减小字号
            if math.ceil(w / (right_bottom_x - left_top_x)) < int(
                            (right_bottom_y - left_top_y) / h):  # math.ceil()上入整数函数
                # 将最适合的字体大小保存到actual_size，供生成json使用
                actual_size = now_size
                # 根据要求的对齐方式进行绘制，left、center、right
                if constraint.align == "left":  # 文本左对齐
                    # 分割行
                    text = text + " "  # 处理最后少一个字问题，方便
                    start = 0
                    end = len(text) - 1
                    lines = []
                    while start < end:
                        for n in range(start, end + 1):
                            try_w, try_h = ft.getsize(text[start:n])
                            if try_w > right_bottom_x - left_top_x:  # 若是当前文本超过约束框宽度则跳出循环进入下一行
                                break
                        lines.append(text[start:n])
                        start = n
                    # 绘制行
                    i = 0  # 当前行号
                    for t in range(len(lines)):
                        draw_img.text((left_top_x, left_top_y + i * h), lines[t], fill=color, font=ft)
                        draw_layer.text((0, i * h), lines[t], fill=color, font=ft)
                        i = i + 1
                elif constraint.align == "center":  # 文本中间对齐
                    # 暂时只支持左对齐，因为中心对齐和右对齐涉及到文本语义理解
                    print("暂时只支持左对齐！")
                else:  # 文本右对齐
                    # 暂是只支持左对齐，因为中心对齐和右对齐涉及到文本语义理解
                    print("暂时只支持左对齐！")

                # 可换行时，box_in_box比较好计算
                box_in_box = (left_top_x, left_top_y, left_top_x+w, left_top_y+h)
                break
    # 制作类似json格式的图层信息，并添加到psd_layers中的'layers'列表中去
    json_layer = {}
    number = len(psd_layers['layers']) + 1  # 图层id
    json_layer['number'] = number
    json_layer['name'] = text

    # json_layer['left'] = box_in_box[0]
    # json_layer['top'] = box_in_box[1]
    # json_layer['width'] = box_in_box[2] - box_in_box[0]
    # json_layer['height'] = box_in_box[3] - box_in_box[1]
    json_layer['left'] = left_top_x
    json_layer['top'] = left_top_y
    json_layer['width'] = right_bottom_x - left_top_x
    json_layer['height'] = right_bottom_y - left_top_y
    json_layer['opacity'] = 1
    # 将制作好的文本图层添加进psd_layers的layers中去
    psd_layers['layers'].append(json_layer)
    return layer_png, psd_layers


# 绘制文本信息（title、subtitle、content）至背景图片上，同时生成单独的图层返回；最后一个参数表示是否可换行
def draw_text(img, psd_layers, text, constraint, color, font, multiline_or_not, path):
    # 根据长宽计算左上角和右下角的绝对位置
    left_top_x, left_top_y, right_bottom_x, right_bottom_y = constraint.get_rect_space(psd_layers['width'],
                                                                                       psd_layers['height'])
    # 按比例缩放约束空间
    PERCENT_TEXT_SPACE = float(constraint.precent)/100
    left_top_x, left_top_y, right_bottom_x, right_bottom_y = shrink_rect(left_top_x, left_top_y, right_bottom_x,
                                                                         right_bottom_y, PERCENT_TEXT_SPACE)
    # 文字绘制的边界：left，top，width，height
    box_in_box = ()
    # 添加到json里面的字体尺寸
    actual_size = 0

    # 设置字体，若有特殊字体要求，则用特殊字体
    if constraint.font_family is not None:
        font = "webFonts/" + constraint.font_family
        #print(font)

    # 设置颜色，若有特殊颜色要求，则用颜色字体
    if constraint.color is not None:
        color = constraint.color

    # 在主背景图img上和图层图img_layer上都进行绘制
    draw_img = ImageDraw.Draw(img)
    layer_png = Image.new(mode='RGBA', size=(right_bottom_x - left_top_x, right_bottom_y - left_top_y))
    draw_layer = ImageDraw.Draw(layer_png)
    if multiline_or_not is False:  # 标题和副标题不可换行
        for now_size in range(int(constraint.max_size), int(constraint.min_size), -2):
            ft = ImageFont.truetype(font, now_size)
            w, h = ft.getsize(text)
            # 由于相同字号的不同字体的长宽都有所不同，所以要先判断整个字符串的长宽，若超出约束空间则减小字号
            if w < (right_bottom_x - left_top_x) and h < (right_bottom_y - left_top_y):
                # 将最适合的字体大小保存到actual_size，供生成json使用
                actual_size = now_size
                # 根据要求的对齐方式进行绘制，left、center、right
                if constraint.align == "left":  # 文本左对齐
                    draw_img.text((left_top_x, left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2), text,
                                  fill=color, font=ft)
                    draw_layer.text((0, (right_bottom_y - left_top_y) / 2 - h / 2), text, fill=color, font=ft)
                    box_in_box = (left_top_x, left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2, left_top_x+w, h + left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2)
                elif constraint.align == "center":  # 文本中间对齐
                    draw_img.text((left_top_x + (right_bottom_x - left_top_x) / 2 - w / 2,
                                   left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2), text, fill=color, font=ft)
                    draw_layer.text(
                        ((right_bottom_x - left_top_x) / 2 - w / 2, (right_bottom_y - left_top_y) / 2 - h / 2), text,
                        fill=color, font=ft)
                    box_in_box = (left_top_x + (right_bottom_x - left_top_x) / 2 - w / 2,
                                  left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2, w+left_top_x + (right_bottom_x - left_top_x) / 2 - w / 2, h+left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2)
                elif constraint.align == "right":  # 文本右对齐
                    draw_img.text((right_bottom_x - w, left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2), text,
                                  fill=color, font=ft)
                    draw_layer.text((right_bottom_x - w - left_top_x, (right_bottom_y - left_top_y) / 2 - h / 2), text,
                                    fill=color, font=ft)
                    box_in_box = (right_bottom_x - w, left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2, right_bottom_x, h +left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2)
                else:
                    draw_img.text((left_top_x, left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2), text,
                                  fill=color, font=ft)
                    draw_layer.text((0, (right_bottom_y - left_top_y) / 2 - h / 2), text, fill=color, font=ft)
                    box_in_box = (left_top_x, left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2, left_top_x + w,
                                  h + left_top_y + (right_bottom_y - left_top_y) / 2 - h / 2)
                break
    else:  # content可换行
        for now_size in range(int(constraint.max_size), int(constraint.min_size), -1):
            ft = ImageFont.truetype(font, now_size)
            w, h = ft.getsize(text)
            # 内容文字可换行，若行数不超出约束空间，则可绘制，否则减小字号
            if math.ceil(w / (right_bottom_x - left_top_x)) < int(
                            (right_bottom_y - left_top_y) / h):  # math.ceil()上入整数函数
                # 将最适合的字体大小保存到actual_size，供生成json使用
                actual_size = now_size
                # 根据要求的对齐方式进行绘制，left、center、right
                if constraint.align == "left":  # 文本左对齐
                    # 分割行
                    text = text + " "  # 处理最后少一个字问题，方便
                    start = 0
                    end = len(text) - 1
                    lines = []
                    while start < end:
                        for n in range(start, end + 1):
                            try_w, try_h = ft.getsize(text[start:n])
                            if try_w > right_bottom_x - left_top_x:  # 若是当前文本超过约束框宽度则跳出循环进入下一行
                                break
                        lines.append(text[start:n])
                        start = n
                    # 绘制行
                    i = 0  # 当前行号
                    for t in range(len(lines)):
                        draw_img.text((left_top_x, left_top_y + i * h), lines[t], fill=color, font=ft)
                        draw_layer.text((0, i * h), lines[t], fill=color, font=ft)
                        i = i + 1
                elif constraint.align == "center":  # 文本中间对齐
                    # 暂时只支持左对齐，因为中心对齐和右对齐涉及到文本语义理解
                    print("暂时只支持左对齐！")
                    #========================代码通同left左对齐，之后要改===============
                    text = text + " "
                    start = 0
                    end = len(text) - 1
                    lines = []
                    while start < end:
                        for n in range(start, end + 1):
                            try_w, try_h = ft.getsize(text[start:n])
                            if try_w > right_bottom_x - left_top_x:
                                break
                        lines.append(text[start:n])
                        start = n
                    i = 0
                    for t in range(len(lines)):
                        draw_img.text((left_top_x, left_top_y + i * h), lines[t], fill=color, font=ft)
                        draw_layer.text((0, i * h), lines[t], fill=color, font=ft)
                        i = i + 1
                    #==================================================================
                else:  # 文本右对齐
                    # 暂是只支持左对齐，因为中心对齐和右对齐涉及到文本语义理解
                    print("暂时只支持左对齐！")
                    #========================代码通同left左对齐，之后要改===============
                    text = text + " "
                    start = 0
                    end = len(text) - 1
                    lines = []
                    while start < end:
                        for n in range(start, end + 1):
                            try_w, try_h = ft.getsize(text[start:n])
                            if try_w > right_bottom_x - left_top_x:
                                break
                        lines.append(text[start:n])
                        start = n
                    i = 0
                    for t in range(len(lines)):
                        draw_img.text((left_top_x, left_top_y + i * h), lines[t], fill=color, font=ft)
                        draw_layer.text((0, i * h), lines[t], fill=color, font=ft)
                        i = i + 1
                    #==================================================================

                # 可换行时，box_in_box比较好计算
                box_in_box = (left_top_x, left_top_y, left_top_x+w, left_top_y+h)
                break
    # 制作类似json格式的图层信息，并添加到psd_layers中的'layers'列表中去
    json_layer = {}
    number = len(psd_layers['layers']) + 1  # 图层id
    json_layer['number'] = number
    json_layer['name'] = text
    json_layer['left'] = box_in_box[0]
    json_layer['top'] = box_in_box[1]
    json_layer['width'] = box_in_box[2] - box_in_box[0]
    json_layer['height'] = box_in_box[3] - box_in_box[1]
    json_layer['opacity'] = 1
    json_layer_text = {}
    json_layer_text['value'] = text
    json_layer_text_font = {}
    json_layer_text_font["name"] = font  # font文字地址path
    json_layer_text_font['sizes'] = [actual_size, actual_size]
    r, g, b = hex2rgb(color)
    json_layer_text_font['colors'] = [[r, g, b, 255], [r, g, b, 255]]  # 最后一个255是透明度
    json_layer_text_font['alignment'] = "left"
    json_layer_text['font'] = json_layer_text_font
    json_layer_text['left'] = 0
    json_layer_text['top'] = 0
    json_layer_text['right'] = 0
    json_layer_text['bottom'] = 0
    json_layer_text_transform = {}
    json_layer_text_transform['xx'] = 1
    json_layer_text_transform['xy'] = 0
    json_layer_text_transform['yx'] = 0
    json_layer_text_transform['yy'] = 1
    json_layer_text_transform['tx'] = box_in_box[0]
    json_layer_text_transform['ty'] = box_in_box[1]
    json_layer_text['transform'] = json_layer_text_transform
    json_layer['text'] = json_layer_text
    # 将制作好的文本图层添加进psd_layers的layers中去
    psd_layers['layers'].append(json_layer)
    return layer_png, psd_layers


# 绘制图片信息（logo、photo）至背景图片上，同时生成单独的图层返回
def draw_photo(img, psd_layers, url, constraint, WIDTH, HEIGHT, shape):
    if shape == 'Q':
        if constraint.is_rect() is True:
            layer_png, psd_layers = draw_img_in_rect(img, psd_layers, url, constraint, WIDTH, HEIGHT,True)  # 一般不支持裁剪
        else:
            layer_png, psd_layers = draw_img_in_rect(img, psd_layers, url, constraint, WIDTH, HEIGHT,True)  # 一般不支持裁剪
            # draw_img_in_quadrilateral(img, url, constraint, WIDTH, HEIGHT, PERCENT_IMG_SPACE) # 若是不规则四边形，必须裁剪
    elif shape == 'T':
        draw_img_in_triangle()
    elif shape == 'C':
        draw_img_in_circle()

    return layer_png, psd_layers


# 绘制图像信息至长方形约束框里，同时生成单独的图层返回
def draw_img_in_rect(img, psd_layers, url, constraint, WIDTH, HEIGHT, mode):
    # 根据长宽计算左上角和右下角的绝对位置
    left_top_x, left_top_y, right_bottom_x, right_bottom_y = constraint.get_rect_space(WIDTH, HEIGHT)
    # 按比例缩放约束空间
    PERCENT_IMG_SPACE = float(constraint.precent)/100
    LT_x, LT_y, RB_x, RB_y = shrink_rect(left_top_x, left_top_y, right_bottom_x, right_bottom_y, PERCENT_IMG_SPACE)
    # resize操作需要整数,box为图片缩放大小和粘贴区域
    box = (LT_x, LT_y, RB_x, RB_y)
    box_resize = ()  # 实际在原始图中绘制的位置

    # 获取网络or本地图片
    try:  # 获取网络地址
        response = requests.get(url)
        photo = Image.open(BytesIO(response.content))
        #photo = photo.convert('RGBA')
    except Exception as e:  # 网络地址获取失败的话获取本地图片
        photo = Image.open(url)

    #判断是否有人脸，或者感兴趣区域ROI，并将ROI移动到布局显著性区域
    face_location = face_detect(photo)
    if face_location is not None:  # 有人脸
        # 根据长宽计算人脸放置位置的左上角和右下角的绝对位置
        LT_face_x, LT_face_y, RB_face_x, RB_face_y = constraint.get_face_space(WIDTH, HEIGHT)
        # 分别计算：①上传照片中检测到的真实人脸的中心位置；②约束框中人脸放置位置的中心点
        face_from_center_x = int(face_location[0] + face_location[2] / 2)
        face_from_center_y = int(face_location[1] + face_location[3] / 2)
        face_to_center_x = int((LT_face_x + RB_face_x)/2)
        face_to_center_y = int((LT_face_y + RB_face_y) / 2)
        # 分别计算：①源图中人脸宽高；②粘贴目标图中人脸约束空间的宽高
        face_from_W = face_location[2]
        face_from_H = face_location[3]
        face_to_W = RB_face_x - LT_face_x
        face_to_H = RB_face_y - LT_face_y

        if face_from_W/face_from_H > face_to_W/face_to_H :
            # 计算from图中左上角的横纵坐标（from_left_width_x，from_up_height_y）
            from_left_width = (face_to_center_x - LT_x)*(face_from_W/2)/(face_to_W/2)
            from_left_width_x = face_from_center_x - from_left_width
            from_top_height = (face_to_center_y - LT_y)*(face_from_H/2)/((face_to_W/2)*face_from_H/face_from_W)
            from_top_height_y = face_from_center_y - from_top_height
            # 计算from图中右下角的横纵坐标（from_right_width_x，from_bottom_height_y）
            from_right_width = (RB_x - face_to_center_x)*(face_from_W/2)/(face_to_W/2)
            from_right_width_x = face_from_center_x + from_right_width
            from_bottom_height = (RB_y - face_to_center_y)*(face_from_H/2)/((face_to_W/2)*face_from_H/face_from_W)
            from_bottom_height_y = face_from_center_y+from_bottom_height
            # 从源照片中截取人脸显著部门
            photo_crop = photo.crop((from_left_width_x,from_top_height_y,from_right_width_x,from_bottom_height_y))
            temp_photo = photo_crop.resize((box[2]-box[0],box[3]-box[1]))
            box_resize = box
            img.paste(temp_photo,box_resize)
    else:  # 无人脸
        if mode is True:  # 允许裁剪
            w, h = photo.size
            box_w = box[2] - box[0]
            box_h = box[3] - box[1]
            if w / h < box_w / box_h:  # 宽度优先等比例缩放
                temp_photo = photo.resize((box_w, int(h / w * box_w)))  # 宽度优先等比例缩放
                box_crop = (0, int((int(h / w * box_w) - box_h) / 2), box_w, int((int(h / w * box_w) - box_h) / 2) + box_h)
                temp_photo = temp_photo.crop(box_crop)
                box_resize = box
                img.paste(temp_photo, box_resize)  # 在原始背景图的box_resize位置黏贴temp_photo
            else:  # 高度优先等比例缩放
                temp_photo = photo.resize((int(w / h * box_h), box_h))  # 高度优先等比例缩放
                box_crop = (int((int(w / h * box_h) - box_w) / 2), 0, int((int(w / h * box_h) - box_w) / 2) + box_w, box_h)
                temp_photo = temp_photo.crop(box_crop)
                box_resize = box
                img.paste(temp_photo, box_resize)
        else:  # 不允许裁剪，与允许裁剪的缩放方式刚好相反
            w, h = photo.size
            if w / h < (box[2] - box[0]) / (box[3] - box[1]):
                temp_photo = photo.resize((int(w / h * (box[3] - box[1])), box[3] - box[1]))  # 高度优先等比例缩放
                # 根据图片对齐方式计算粘贴的位置box_temp
                if constraint.align == "left":  # 图片左对齐
                    box_resize = (box[0], box[1], box[0] + temp_photo.size[0], box[1] + temp_photo.size[1])
                elif constraint.align == "center":  # 图片中心对齐
                    # 中心对齐时，先计算logo放置位置的左上角的X坐标
                    X = int(((box[2] - box[0]) - (temp_photo.size[0])) / 2 + box[0])
                    box_resize = (X, box[1], X + temp_photo.size[0], box[1] + temp_photo.size[1])
                elif constraint.align == "right":  # 否则就是右对齐
                    box_resize = (box[2] - temp_photo.size[0], box[1], box[2], box[1] + temp_photo.size[1])
                else:  # 默认也是中心对齐
                    X = int(((box[2] - box[0]) - (temp_photo.size[0])) / 2 + box[0])
                    box_resize = (X, box[1], X + temp_photo.size[0], box[1] + temp_photo.size[1])
                # 粘贴图片
                if temp_photo.mode == 'RGBA':
                    img.paste(temp_photo, box_resize, mask=temp_photo)
                else:
                    img.paste(temp_photo, box_resize)
            else:
                temp_photo = photo.resize((box[2] - box[0], int(h / w * (box[2] - box[0]))))  # 宽度优先等比例缩放
                if constraint.align == "top":  # 图片顶端对齐
                    box_resize = (box[0], box[1], box[0] + temp_photo.size[0], box[1] + temp_photo.size[1])
                elif constraint.align == "right":  # 图片中心对齐
                    # 此时，中心对齐时，先计算logo放置位置的左上角的Y坐标
                    Y = int(((box[3] - box[1]) - (temp_photo.size[1])) / 2 + box[1])
                    box_resize = (box[0], Y, box[0] + temp_photo.size[0], Y + temp_photo.size[1])
                elif constraint.align == "bottom":  # 否则就是底端对齐
                    box_resize = (box[0], box[3] - temp_photo.size[1], box[0] + temp_photo.size[0], box[3])
                else:  # 默认也采用中心对齐
                    Y = int(((box[3] - box[1]) - (temp_photo.size[1])) / 2 + box[1])
                    box_resize = (box[0], Y, box[0] + temp_photo.size[0], Y + temp_photo.size[1])
                #粘贴图片
                if temp_photo.mode == 'RGBA':
                    img.paste(temp_photo, box_resize, mask=temp_photo)  # 图片粘贴
                else:
                    img.paste(temp_photo, box_resize)  # 图片粘贴

    # 制作类似json格式的图像图层信息，并添加到psd_layers中的'layers'列表中去
    json_layer = {}
    number = len(psd_layers['layers']) + 1  # 图层id
    json_layer['number'] = number
    json_layer['name'] = "图像图层"
    json_layer['left'] = box_resize[0]
    json_layer['top'] = box_resize[1]
    json_layer['width'] = box_resize[2] - box_resize[0]
    json_layer['height'] = box_resize[3] - box_resize[1]
    json_layer['opacity'] = 1
    # 将制作好的图像图层添加进psd_layers的layers中去
    psd_layers['layers'].append(json_layer)
    return temp_photo, psd_layers


# 绘制图像信息至约束框里，同时生成单独的图层返回
def draw_img_in_quadrilateral(img, url, constraint, WIDTH, HEIGHT):
    # 根据长宽计算不规则四边形的四个角的绝对位置
    LT_x, LT_y, RT_x, RT_y, RB_x, RB_y, LB_x, LB_y = constraint.get_quadrilateral_space(WIDTH, HEIGHT)
    # 按比例缩放约束空间
    PERCENT_IMG_SPACE = float(constraint.precent)/100
    LT_x, LT_y, RT_x, RT_y, RB_x, RB_y, LB_x, LB_y = shrink_quadrilateral(LT_x, LT_y, RT_x, RT_y, RB_x, RB_y, LB_x,
                                                                          LB_y, PERCENT_IMG_SPACE)

    # 计算不规则四边形外接长方形的范围
    min_x = min(LT_x, RT_x, RB_x, LB_x)
    max_x = max(LT_x, RT_x, RB_x, LB_x)
    min_y = min(LT_y, RT_y, RB_y, LB_y)
    max_y = max(LT_y, RT_y, RB_y, LB_y)
    # resize操作需要整数,box为图片缩放大小和粘贴区域
    box = (min_x, min_y, max_x, max_y)
    # 黏贴的图片
    photo = Image.open(url)
    photo = photo.resize((max_x - min_x, max_y - min_y))
    # 黏贴时辅助的掩码
    mask = Image.new('RGB', (max_x - min_x, max_y - min_y), (0, 0, 0, 0))
    draw = ImageDraw.Draw(mask)
    draw.polygon([(LT_x - min_x, LT_y - min_y), (RT_x - min_x, RT_y - min_y), (RB_x - min_x, RB_y - min_y),
                  (LB_x - min_x, LB_y - min_y)], fill=(255, 255, 255))

    # 必须将mask图像转换灰度或者二值化，才能有掩码效果
    mask = mask.convert("L")
    img.paste(photo, box, mask=mask)


"""
# 绘制图像信息至长方形约束框里，同时生成单独的图层返回
def draw_img_in_rect(img, url, constraint, WIDTH, HEIGHT, PERCENT_IMG_SPACE, mode):
    # 根据长宽计算左上角和右下角的绝对位置
    left_top_x, left_top_y, right_bottom_x, right_bottom_y = constraint.get_rect_space(WIDTH, HEIGHT)
    # 按比例缩放约束空间
    LT_x, LT_y, RB_x, RB_y = shrink_rect(left_top_x, left_top_y, right_bottom_x, right_bottom_y, PERCENT_IMG_SPACE)
    # resize操作需要整数,box为图片缩放大小和粘贴区域
    box = (LT_x, LT_y, RB_x, RB_y)

    # 获取网络or本地图片
    try:  # 获取网络地址
        response = req.get(url)
        photo = Image.open(BytesIO(response.content))
    except Exception as e:  # 网络地址获取失败的话获取本地图片
        photo = Image.open(url)

    if mode is True:  # 在长方形的基础上，允许裁剪
        w, h = photo.size
        box_w = box[2] - box[0]
        box_h = box[3] - box[1]
        if w/h < box_w/box_h:  # 宽度优先等比例缩放
            temp_photo = photo.resize((box_w, int(h / w * box_w)))  # 宽度优先等比例缩放
            box_crop = ( 0,int((int(h / w * box_w) - box_h)/2),box_w ,int((int(h / w * box_w) - box_h)/2)+box_h)
            temp_photo = temp_photo.crop(box_crop)
            img.paste(temp_photo, box, mask=temp_photo)  # 在原始地图的box位置黏贴temp_photo
        else:  # 高度优先等比例缩放
            temp_photo = photo.resize((int(w / h * box_h), box_h))  # 高度优先等比例缩放
            box_crop = (int((int(w / h * box_h) - box_w)/2), 0,int((int(w / h * box_h) - box_w)/2)+box_w ,box_h)
            temp_photo = temp_photo.crop(box_crop)
            img.paste(temp_photo, box, mask=temp_photo)
    else:  # 不允许裁剪，与允许裁剪的缩放方式刚好相反
        w, h = photo.size
        if w / h < (box[2] - box[0]) / (box[3] - box[1]):
            temp_photo = photo.resize((int(w / h * (box[3] - box[1])), box[3] - box[1]))  # 高度优先等比例缩放
            # 根据图片对齐方式计算粘贴的位置box_temp
            if constraint.align == "left":  # 图片左对齐
                box_resize = (box[0], box[1], box[0] + temp_photo.size[0], box[1] + temp_photo.size[1])
            elif constraint.align == "center":  # 图片中心对齐
                # 中心对齐时，先计算logo放置位置的左上角的X坐标
                X = int(((box[2] - box[0]) - (temp_photo.size[0]))/2 + box[0])
                box_resize = (X, box[1], X + temp_photo.size[0], box[1] + temp_photo.size[1])
            elif constraint.align == "right":  # 否则就是右对齐
                box_resize = (box[2] - temp_photo.size[0], box[1], box[2], box[1] + temp_photo.size[1])
            else:  # 默认也是中心对齐
                X = int(((box[2] - box[0]) - (temp_photo.size[0]))/2 + box[0])
                box_resize = (X, box[1], X + temp_photo.size[0], box[1] + temp_photo.size[1])
            img.paste(temp_photo, box_resize, mask=temp_photo)  # 图片粘贴
        else:
            temp_photo = photo.resize((box[2] - box[0], int(h / w * (box[2] - box[0]))))  # 宽度优先等比例缩放
            if constraint.align == "top":  # 图片顶端对齐
                box_resize = (box[0], box[1], box[0] + temp_photo.size[0], box[1] + temp_photo.size[1])
            elif constraint.align == "right":  # 图片中心对齐
                # 此时，中心对齐时，先计算logo放置位置的左上角的Y坐标
                Y = int(((box[3] - box[1]) - (temp_photo.size[1]))/2 + box[1])
                box_resize = (box[0], Y, box[0] + temp_photo.size[0], Y + temp_photo.size[1])
            elif constraint.align == "bottom" :  # 否则就是底端对齐
                box_resize = (box[0], box[3] - temp_photo.size[1], box[0] + temp_photo.size[0], box[3])
            else:  # 默认也采用中心对齐
                Y = int(((box[3] - box[1]) - (temp_photo.size[1]))/2 + box[1])
                box_resize = (box[0], Y, box[0] + temp_photo.size[0], Y + temp_photo.size[1])
            img.paste(temp_photo, box_resize, mask=temp_photo)


# 绘制图像信息至约束框里，同时生成单独的图层返回
def draw_img_in_quadrilateral(img, url, constraint, WIDTH, HEIGHT, PERCENT_IMG_SPACE):
    # 根据长宽计算不规则四边形的四个角的绝对位置
    LT_x, LT_y, RT_x, RT_y, RB_x, RB_y, LB_x, LB_y = constraint.get_quadrilateral_space(WIDTH, HEIGHT)
    # 按比例缩放约束空间
    LT_x, LT_y, RT_x, RT_y, RB_x, RB_y, LB_x, LB_y = shrink_quadrilateral(LT_x, LT_y, RT_x, RT_y, RB_x, RB_y, LB_x, LB_y, PERCENT_IMG_SPACE)

    # 计算不规则四边形外接长方形的范围
    min_x = min(LT_x, RT_x, RB_x, LB_x)
    max_x = max(LT_x, RT_x, RB_x, LB_x)
    min_y = min(LT_y, RT_y, RB_y, LB_y)
    max_y = max(LT_y, RT_y, RB_y, LB_y)
    # resize操作需要整数,box为图片缩放大小和粘贴区域
    box = (min_x, min_y, max_x, max_y)
    # 获取网络or本地图片
    try:  # 获取网络地址
        response = req.get(url)
        photo = Image.open(BytesIO(response.content))
    except Exception as e:  # 网络地址获取失败的话获取本地图片
        photo = Image.open(url)

    w, h = photo.size
    if w / h < (box[2] - box[0]) / (box[3] - box[1]):
        temp_photo = photo.resize((int(w / h * (box[3] - box[1])), box[3] - box[1]))  # 高度优先等比例缩放
        # 根据图片对齐方式计算粘贴的位置box_temp
        if constraint.align == "left":  # 图片左对齐
            box_resize = (box[0], box[1], box[0] + temp_photo.size[0], box[1] + temp_photo.size[1])
        elif constraint.align == "center":  # 图片中心对齐
            # 中心对齐时，先计算logo放置位置的左上角的X坐标
            X = int(((box[2] - box[0]) - (temp_photo.size[0])) / 2 + box[0])
            box_resize = (X, box[1], X + temp_photo.size[0], box[1] + temp_photo.size[1])
        elif constraint.align == "right":  # 否则就是右对齐
            box_resize = (box[2] - temp_photo.size[0], box[1], box[2], box[1] + temp_photo.size[1])
        else:  # 默认也是中心对齐
            X = int(((box[2] - box[0]) - (temp_photo.size[0])) / 2 + box[0])
            box_resize = (X, box[1], X + temp_photo.size[0], box[1] + temp_photo.size[1])

        if constraint.align == "left":  # 图片左对齐
            box_in_box = (0, 0, temp_photo.size[0], temp_photo.size[1])
        elif constraint.align == "center":  # 图片中心对齐
            # 中心对齐时，先计算logo放置位置的左上角的X坐标
            X = int(((box[2] - box[0]) - (temp_photo.size[0])) / 2 )
            box_in_box = (X, 0, X + temp_photo.size[0], temp_photo.size[1])
        elif constraint.align == "right":  # 否则就是右对齐
            box_in_box = (box[2] - temp_photo.size[0], box[1], box[2], box[1] + temp_photo.size[1])
        else:  # 默认也是中心对齐
            X = int(((box[2] - box[0]) - (temp_photo.size[0])) / 2 )
            box_in_box = ((box[2] - box[0])-temp_photo.size[0], 0, box[2] - box[0], temp_photo.size[1])

        # 黏贴时辅助的掩码
        mask = Image.new('RGB', (temp_photo.size[0], temp_photo.size[1]), (0, 0, 0))
        mask2 = Image.new('RGB', (box[2] - box[0], box[3] - box[1]), (0, 0, 0))
        draw = ImageDraw.Draw(mask)
        draw.polygon([(LT_x - min_x, LT_y - min_y), (RT_x - min_x, RT_y - min_y), (RB_x - min_x, RB_y - min_y),
                      (LB_x - min_x, LB_y - min_y)], fill=(255, 255, 255))

        #r, g, b, alpha = mask.split()
        photo2 = mask2.paste(temp_photo, box_in_box, mask=mask)
        photo2 = cv2.cvtColor(np.asarray(photo2), cv2.COLOR_RGB2BGR)
        img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
        rows,cols,channels = photo2.shape
        roi = img[min_x:min_x + rows, min_y:min_y + cols]
        photo2gray = cv2.cvtColor(photo2, cv2.COLOR_RGB2GRAY)
        ret, mask = cv2.threshold(photo2gray, 10, 255, cv2.THRESH_BINARY)
        photo2_inv = cv2.bitwise_not(mask)
        img_bg = cv2.bitwise_and(roi, roi, mask=photo2_inv)
        img_fg = cv2.bitwise_and(photo2, photo2, mask=mask)
        dst = cv2.add(img_bg, img_fg)
        img[min_x:min_x + rows, min_y:min_y + cols] = dst
        cv2.imshow('res',img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        # # 必须将mask图像转换灰度或者二值化，才能有掩码效果
        # mask3 = mask2
        # r,g,b,alpha = mask2.split()
        # mask3.save("outputPosters/xjw.png")
        # # mask4 = Image.open("outputPosters/xjw.png")
        # # mask5 = mask4.convert('L')
        # img.paste(mask3, box, mask=g)  # 图片粘贴
    else:
        temp_photo = photo.resize((box[2] - box[0], int(h / w * (box[2] - box[0]))))  # 宽度优先等比例缩放
        if constraint.align == "top":  # 图片顶端对齐
            box_resize = (box[0], box[1], box[0] + temp_photo.size[0], box[1] + temp_photo.size[1])
        elif constraint.align == "right":  # 图片中心对齐
            # 此时，中心对齐时，先计算logo放置位置的左上角的Y坐标
            Y = int(((box[3] - box[1]) - (temp_photo.size[1])) / 2 + box[1])
            box_resize = (box[0], Y, box[0] + temp_photo.size[0], Y + temp_photo.size[1])
        elif constraint.align == "bottom":  # 否则就是底端对齐
            box_resize = (box[0], box[3] - temp_photo.size[1], box[0] + temp_photo.size[0], box[3])
        else:  # 默认也采用中心对齐
            Y = int(((box[3] - box[1]) - (temp_photo.size[1])) / 2 + box[1])
            box_resize = (box[0], Y, box[0] + temp_photo.size[0], Y + temp_photo.size[1])
        img.paste(temp_photo, box_resize, mask=temp_photo)


    # # photo = photo.resize((max_x - min_x, max_y - min_y))
    # # 黏贴时辅助的掩码
    # mask = Image.new('RGB', (max_x - min_x, max_y - min_y), (0, 0, 0, 0))
    # draw = ImageDraw.Draw(mask)
    # draw.polygon([(LT_x - min_x, LT_y - min_y), (RT_x - min_x, RT_y - min_y), (RB_x - min_x, RB_y - min_y),
    #               (LB_x - min_x, LB_y - min_y)], fill=(255, 255, 255))
    # # 必须将mask图像转换灰度或者二值化，才能有掩码效果
    # mask = mask.convert("L")
    # mask.paste()
    # img.paste(photo, box, mask=mask)
"""


def draw_img_in_triangle():
    print('sanjiaoxing')


def draw_img_in_circle():
    print('yuanxing')


# 按百分比缩小长方形约束空间
def shrink_rect(left_top_x, left_top_y, right_bottom_x, right_bottom_y, SPACE_PERCENT):
    # 先计算减小的留白宽度
    offset_x = (right_bottom_x - left_top_x) * (1 - SPACE_PERCENT) / 2
    offset_y = (right_bottom_y - left_top_y) * (1 - SPACE_PERCENT) / 2
    return int(left_top_x + offset_x), int(left_top_y + offset_y), int(right_bottom_x - offset_x), int(
        right_bottom_y - offset_y)


# 按百分比缩小不规则四边形约束空间，  看起来简单，其实计算较为复杂
def shrink_quadrilateral(LT_x, LT_y, RT_x, RT_y, RB_x, RB_y, LB_x, LB_y, SPACE_PERCENT):
    # 先计算不规则四边形外接长方形的范围
    min_x = min(LT_x, RT_x, RB_x, LB_x)
    max_x = max(LT_x, RT_x, RB_x, LB_x)
    min_y = min(LT_y, RT_y, RB_y, LB_y)
    max_y = max(LT_y, RT_y, RB_y, LB_y)
    # 计算四个点坐标值在外接长方形中相对位置
    p_LT_x = (LT_x - min_x) / (max_x - min_x)
    p_LT_y = (LT_y - min_y) / (max_y - min_y)
    p_RT_x = (RT_x - min_x) / (max_x - min_x)
    p_RT_y = (RT_y - min_y) / (max_y - min_y)
    p_RB_x = (RB_x - min_x) / (max_x - min_x)
    p_RB_y = (RB_y - min_y) / (max_y - min_y)
    p_LB_x = (LB_x - min_x) / (max_x - min_x)
    p_LB_y = (LB_y - min_y) / (max_y - min_y)
    # 再计算减小的留白宽度
    offset_x = (max_x - min_x) * (1 - SPACE_PERCENT) / 2
    offset_y = (max_y - min_y) * (1 - SPACE_PERCENT) / 2
    # 新的外接长方形的位置
    new_LT_x = min_x + offset_x + p_LT_x * (max_x - min_x) * SPACE_PERCENT
    new_LT_y = min_y + offset_y + p_LT_y * (max_y - min_y) * SPACE_PERCENT
    new_RT_x = min_x + offset_x + p_RT_x * (max_x - min_x) * SPACE_PERCENT
    new_RT_y = min_y + offset_y + p_RT_y * (max_y - min_y) * SPACE_PERCENT
    new_RB_x = min_x + offset_x + p_RB_x * (max_x - min_x) * SPACE_PERCENT
    new_RB_y = min_y + offset_y + p_RB_y * (max_y - min_y) * SPACE_PERCENT
    new_LB_x = min_x + offset_x + p_LB_x * (max_x - min_x) * SPACE_PERCENT
    new_LB_y = min_y + offset_y + p_LB_y * (max_y - min_y) * SPACE_PERCENT
    return int(new_LT_x), int(new_LT_y), int(new_RT_x), int(new_RT_y), int(new_RB_x), int(new_RB_y), int(new_LB_x), int(
        new_LB_y)


# 色彩值十六进制rgb格式
def hex2rgb(hex):
    hex = hex.strip(' #')
    reb = hex[0:2]
    r = int(reb, 16)
    green = hex[2:4]
    g = int(green, 16)
    blue = hex[4:6]
    b = int(blue, 16)
    return r, g, b


# 人脸检测，
def face_detect(photo):
    # 读取训练好的分类器，haarcascade_frontalface_default.xml存储在cv2包的data文件夹内
    face_cascade = cv2.CascadeClassifier('haarcascade/haarcascade_frontalface_default.xml')
    # PIL.Image转换成opencv格式
    img = cv2.cvtColor(np.asarray(photo),cv2.COLOR_RGB2BGR)
    # 图像灰度化
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

    # 运用haar分类器扫描图像识别人脸。detectMultiScale函数中参数：
    #       ① scaleFacter：人脸检测过程中每次迭代时压缩率；
    #       ② minNeighbors：每个人脸矩形保留近邻数目的最小值
    # 检测结果：返回人脸矩形数组
    faces = face_cascade.detectMultiScale(gray,1.9,5)

    # # 其实这个for循环暂时没用，因为现阶段上传的单人脸
    # for (x,y,w,h) in faces:
    #     img = cv2.rectangle(img,(x,y),(x+w,y+h),(255,0,0),2)
    # cv2.namedWindow('adf',cv2.WINDOW_NORMAL)
    # cv2.imshow('adf',img)
    # cv2.waitKey(0)

    # opencv转换成PIL.Image格式
    photo = Image.fromarray(cv2.cvtColor(img,cv2.COLOR_BGR2RGB))

    if len(faces) >= 1:
        return faces[0]
    else:
        return None




if __name__ == '__main__':
    app = Flask(__name__)
    CORS(app, resources=r'/*')  # r'/*'是通配符，让本服务器所有的URL都允许跨域请求

    # @app.route('/hello', methods=['GET', 'POST'])  # app.route装饰器映射URL和执行的函数，这个设置将根URL映射到了hello_world函数上
    # def smart_poster():
    #     if request.method == 'POST':
    #         send_result()
    #         return '海报制作中!'

    @app.route('/smartposter',methods=['GET','POST'])  # app.route装饰器映射URL和执行的函数，这个设置将根URL映射到了hello_world函数上
    def smart_poster():
        if request.method == 'POST':
            # 计算海报制作时间，在 Unix 系统中，建议使用 time.time()，在 Windows 系统中，建议使用 time.clock()
            start_all =time.time()  # time.time()为1970.1.1到当前时间的毫秒数
            # 方式一：获取json数据

            start_before = time.time()
            data = request.get_data()
            json_data = json.loads(data.decode("utf-8"))
            end_before = time.time()
            print(json_data)

            start_do = time.time()
            posters_result = produce_posters(json_data)
            end_do = time.time()

            start_after = time.time()
            send_posters_info(posters_result)
            end_after = time.time()

            # 结束时间
            end_all = time.time()
            print("all runing time : %d s " % (end_all - start_all))
            print("before runing time : %d s " % (end_before - start_before))
            print("do runing time : %d s " % (end_do - start_do))
            print("after runing time : %d s " % (end_after - start_after))

            # # 方式二：获取form表单数据
            # uid = request.form.get('user_id')
            # taskid = request.form.get('taskid')
            # style = request.form.get('title')
            # subtitle = request.form.get('subtitle')
            # content = request.form.get('content')
            # logo = request.form.get('logo')
            # photo = request.form.get('photo')
            # post_info = {'uid':uid,'taskid':taskid,'style':style,'subtitle':subtitle,'content':content,'logo':logo,'photo':photo}
            # produce_posters(post_info)
        return '海报制作中!'

    # 访问方式:  http://127.0.0.1:5050/image/?imgurl=background/happy1.jpg
    @app.route('/image/', methods=['GET', 'POST'])
    def get_layer_png():
        # img = Image.open(imgurl)
        # print(img)
        # resp = Response(img, mimetype='image/jpeg')
        imgurl = request.args.get('imgurl')
        img = Image.open(imgurl)
        byte_io = BytesIO()
        img.save(byte_io, 'PNG')
        byte_io.seek(0)
        # resq = Response(img, mimetype="image/jpeg")
        # str = "/background/happy1.jpg"

        return send_file(byte_io, mimetype='image/png', cache_timeout=0)

    app.run(host='0.0.0.0', port=5050, debug=True,threaded = True)
    # 如果服务开启成功，则通知后端服务
    # response = requests.get()




    #
    # # ====================================小测试模块===================================
    # photo = Image.open('background/kuang.jpg')
    # face_detect(photo)






    # for fontsize in (style_layout.title.max_size, style_layout.title.min_size):
    # src = cv.imread("background/happy1.jpg")
    # size=src.shape
    # width=size[0]/2
    # height=size[1]/2
    # print ("%d  %d  %d"%(width,height,size[2]))
    # cv.namedWindow("name window",cv.WINDOW_AUTOSIZE)
    # new_src=cv.resize(src,(int(height),int(width)),cv.INTER_CUBIC)#变换图像尺寸
    #
    # #定义文字类型
    # # font=ImageFont.truetype("Fonts/mygdmc.otf",90)
    # # draw=ImageDraw.Draw(new_src)
    # # draw.text((100,100),u"春节有优惠",(133,21,213),font)
    # cv.putText(new_src,u"what the",(100,100),cv.FONT_HERSHEY_COMPLEX,1,(233,255,255),1)
    #
    # cv.imshow("name window",new_src)
    # cv.imwrite("outputPosters/xjw.jpg",new_src)
    # cv.waitKey(0)#等待下一个操作，才会消失，释放内存
    # cv.destroyAllWindows()