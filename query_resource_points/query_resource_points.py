
from PIL import Image,ImageMath
from io import BytesIO
from loguru import logger
import json
import os
import time
import base64
import httpx
import asyncio
import shutil


MAPLIST_URL     = 'https://api-static.mihoyo.com/common/srmap/sr_map/v1/map/tree?' #所有地图名称
POINT_LIST_URL  = 'https://api-static.mihoyo.com/common/srmap/sr_map/v1/map/point/list?map_id=' #当前地图的标记，包含坐标与资源名称
LABEL_URL       = 'https://api-static.mihoyo.com/common/srmap/sr_map/v1/map/label/tree?map_id=' #所有资源汇总
MAP_URL         = "https://api-static.mihoyo.com/common/srmap/sr_map/v1/map/info?map_id=" #当前地图图片，包含区域名字
APP_LABEL       = 'app_sn=sr_map&lang=zh-cn' #请求标签，必须附加在url结尾

header = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36'

FILE_PATH = os.path.dirname(__file__)

MAP_PATH = os.path.join(FILE_PATH,"icon","map_icon.jpg")
Image.MAX_IMAGE_PIXELS = None


CENTER = None
ORIGIN = None

zoom = 0.5
resource_icon_offset = (-int(150*0.5*zoom),-int(150*zoom))
map_list = []
map_origin_list = []

data = {
    "all_resource_type":{
        # 这个字典保存所有资源类型，
        # "1": {
        #         "id": 1,
        #         "name": "传送点",
        #         "icon": "",
        #         "parent_id": 0,
        #         "depth": 1,
        #         "node_type": 1,
        #         "jump_type": 0,
        #         "jump_target_id": 0,
        #         "display_priority": 0,
        #         "children": []
        #     },
    },
    "can_query_type_list":{
        # 这个字典保存所有可以查询的资源类型名称和ID，这个字典只有名称和ID
        # 上边字典里"depth": 2的类型才可以查询，"depth": 1的是1级目录，不能查询
        # "七天神像":"2"
        # "风神瞳":"5"

    },
    "all_resource_point_list" :[
            # 这个列表保存当前地图资源点的数据
            # {
            #     "id": 2740,
            #     "label_id": 68,
            #     "x_pos": -1789,
            #     "y_pos": 2628,
            #     "author_name": "✟紫灵心✟",
            #     "ctime": "2020-10-29 10:41:21",
            #     "display_state": 1
            # },
    ],
    "date":"" #记录上次更新"all_resource_point_list"的日期
}

async def get_map_pointlist(map_num):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url=POINT_LIST_URL + str(map_num) + "&"+APP_LABEL)
        if resp.status_code != 200:
            raise ValueError(f"获取地图资源失败，错误代码 {resp.status_code}")
        map_list = resp.content
        return resp.content
        

async def download_icon(url):
    # 下载图片，返回Image对象
    async with httpx.AsyncClient() as client:
        resp = await client.get(url=url)
        if resp.status_code != 200:
            raise ValueError(f"获取图片数据失败，错误代码 {resp.status_code}")
        icon = resp.content
        return Image.open(BytesIO(icon))

async def download_json(url):
    # 获取资源数据，返回 JSON
    async with httpx.AsyncClient() as client:
        resp = await client.get(url=url)
        if resp.status_code != 200:
            raise ValueError(f"获取资源点数据失败，错误代码 {resp.status_code}")
        return resp.json()


async def up_icon_image(sublist):
    # 检查是否有图标，没有图标下载保存到本地
    id = sublist["id"]
    icon_path = os.path.join(FILE_PATH,"icon",f"{id}.png")

    if not os.path.exists(icon_path):
        logger.info(f"正在更新资源图标 {id}")
        icon_url = sublist["icon"]
        icon = await download_icon(icon_url)
        icon = icon.resize((150, 150))

        box_alpha = Image.open(os.path.join(FILE_PATH,"icon","box_alpha.png")).getchannel("A")
        box = Image.open(os.path.join(FILE_PATH,"icon","box.png"))

        try:
            icon_alpha = icon.getchannel("A")
            icon_alpha = ImageMath.eval("convert(a*b/256, 'L')", a=icon_alpha, b=box_alpha)
        except ValueError:
            # 米游社的图有时候会没有alpha导致报错，这时候直接使用box_alpha当做alpha就行
            icon_alpha = box_alpha

        icon2 = Image.new("RGBA", (150, 150), "#00000000")
        icon2.paste(icon, (0, 0))

        bg = Image.new("RGBA", (150, 150), "#00000000")
        bg.paste(icon2, mask=icon_alpha)
        bg.paste(box, mask=box)

        with open(icon_path, "wb") as icon_file:
            bg.save(icon_file)


async def up_label_and_point_list():
    logger.info(f"正在更新资源点数据")
    label_data = await download_json(LABEL_URL + "3&" + APP_LABEL)
    for label in label_data["data"]["tree"]:
        data["all_resource_type"][str(label["id"])] = label
        for sublist in label["children"]:
            data["all_resource_type"][str(sublist["id"])] = sublist
            data["can_query_type_list"][sublist["name"]] = str(sublist["id"])
            await up_icon_image(sublist)
        label["children"] = []
    data["date"] = time.strftime("%d")
    
    for index, map in enumerate(map_list):
        label_data = await download_json(POINT_LIST_URL + str(map["id"]) + "&" + APP_LABEL)
        label_list = []
        for label in label_data["data"]["label_list"]:
            label_list += [label["id"]]
        map_list[index] = {"id": map["id"], "upname": map["upname"], "name":map["name"], "origin": map["origin"], "resource":label_list}
    data["date"] = time.strftime("%d")
    logger.info(f"资源点数据更新完成")

async def download_map(map_id):
    # 下载地图文件
    global map_origin_list
    map_info = await download_json(MAP_URL + str(map_id) + "&" + APP_LABEL)
    map_info = map_info["data"]["info"]["detail"]
    if(map_info == ""):
            return
    map_info = json.loads(map_info)
    map_origin = map_info["origin"]
    map_path = os.path.join(FILE_PATH,"maps",f"map_{map_id}.png")
    if not os.path.exists(map_path):
        logger.info(f"正在下载地图{map_id}图片")
        map_url = map_info['slices'][0][0]["url"]
        map = await download_icon(map_url)
        with open(map_path, "wb") as icon_file:
            map.save(icon_file)
        # map_origin_list += [{"id":map_id,"origin":map_origin}]
    for index, map in enumerate(map_list):
        if (map["id"] == map_id):
            map_list[index] = {"id": map["id"], "upname": map["upname"], "name": map["name"], "origin": map_origin}

    
async def up_map():
    logger.info(f"正在更新地图数据")
    map_list_info = await download_json(MAPLIST_URL + APP_LABEL)
    for maps_tree in map_list_info["data"]["tree"]:
        if("children" in maps_tree):
            for map in maps_tree["children"]:
                global map_list
                map_list += [{"id": map["id"], "upname": maps_tree["name"], "name":map["name"]}]
                await download_map(map["id"])
    logger.info(f"地图数据更新完成")


async def init_point_list_and_map():
    await up_map()
    await up_label_and_point_list()
    with open(os.path.join(FILE_PATH, f"map_list.json"), "w", encoding='utf8') as map_list_json:
        json.dump(map_list, map_list_json, ensure_ascii=False, indent=2)
    



# 初始化
loop = asyncio.get_event_loop()
loop.run_until_complete(init_point_list_and_map())




class Resource_map(object):

    def __init__(self,resource_name,map_id):
        global CENTER
        self.resource_id = str(data["can_query_type_list"][resource_name])
        map_path = os.path.join(FILE_PATH,"maps",f"map_{map_id}.png")
        self.map_id = map_id
        self.map_image = Image.open(map_path)
        self.map_size = self.map_image.size

        # 地图要要裁切的左上角和右下角坐标
        # 这里初始化为地图的大小
        self.x_start = self.map_size[0]
        self.y_start = self.map_size[1]
        CENTER = [self.map_size[0], self.map_size[1]]
        self.resource_icon = Image.open(self.get_icon_path())
        self.resource_icon = self.resource_icon.resize((int(150*zoom), int(150*zoom)))

        self.resource_xy_list = self.get_resource_point_list()

    def get_icon_path(self):
        # 检查有没有图标，有返回正确图标，没有返回默认图标
        icon_path = os.path.join(FILE_PATH, "icon", f"{self.resource_id}.png")

        if os.path.exists(icon_path):
            return icon_path
        else:
            return os.path.join(FILE_PATH, "icon", "0.png")

    def get_resource_point_list(self):
        temp_list = []
        for resource_point in data["all_resource_point_list"]:
            if str(resource_point["label_id"]) == self.resource_id:
                # 获取xy坐标
                x = resource_point["x_pos"]
                y = resource_point["y_pos"]
                temp_list.append((int(x), int(y)))
        return temp_list

    def paste(self):
        for x, y in self.resource_xy_list:
            # 把资源图片贴到地图上
            # 这时地图已经裁切过了，要以裁切后的地图左上角为中心再转换一次坐标
            x += ORIGIN[0]
            y += ORIGIN[1]
            self.map_image.paste(self.resource_icon, (x + resource_icon_offset[0], y + resource_icon_offset[1]), self.resource_icon)
            # self.map_image.paste(self.resource_icon,(x, y),self.resource_icon)

    def get_cq_cod(self):

        if not self.resource_xy_list:
            return "没有这个资源的信息"

        # self.crop()

        self.paste()

        bio = BytesIO()
        self.map_image.save(bio, format='JPEG')
        base64_str = 'base64://' + base64.b64encode(bio.getvalue()).decode()

        return f"[CQ:image,file={base64_str}]"

    def save_img(self):
        if not self.resource_xy_list:
            return "没有这个资源的信息"
        self.paste()
        self.map_image = self.map_image.convert('RGB')
        with open(os.path.join(FILE_PATH, "tmp",f"map_{self.map_id}_res{self.resource_id}.jpg"), "wb") as tmp_img:
            self.map_image.save(tmp_img, format='JPEG')
    
    def get_BIO(self):
        self.paste()
        bio = BytesIO()
        self.map_image = self.map_image.convert('RGB')
        self.map_image.save(bio, format='JPEG')
        return bio
         
    def get_resource_count(self):
        return len(self.resource_xy_list)

async def check_resource_on_map(resource_name):
    for map in map_list:
        current_map = await get_map_pointlist(map["id"])
        

async def get_resource_map_mes(name):

    if data["date"] !=  time.strftime("%d"):
        await init_point_list_and_map()

    if not (name in data["can_query_type_list"]):
        return f"没有 {name} 这种资源。\n发送 星铁资源列表 查看所有资源名称"

    try :
        shutil.rmtree(os.path.join(FILE_PATH, "tmp"))
    except:
        os.mkdir(os.path.join(FILE_PATH, "tmp"))
    else:
        os.mkdir(os.path.join(FILE_PATH, "tmp"))   
    resource_id = int(data["can_query_type_list"][name])
    img_list = []
    for map in map_list:
        if(resource_id in map["resource"]):
            global ORIGIN
            map_id = map["id"]
            label_data = await download_json(f"{POINT_LIST_URL}{map_id}&{APP_LABEL}")
            data["all_resource_point_list"] = label_data["data"]["point_list"]
            ORIGIN = map["origin"]
            Resource_map(name, map_id).get_BIO()
            
            
            # with open(os.path.join(FILE_PATH, "tmp",f"map_{map_id}_res{resource_id}.png"), "wb") as tmp_img:
            #     map_img.save(tmp_img)
    # count = map.get_resource_count()

    if not count:
        return f"没有找到 {name} 资源的位置，可能米游社wiki还没更新。"

    mes = f"资源 {name} 的位置如下\n"
    mes += map.get_cq_cod()

    mes += f"\n\n※ {name} 一共找到 {count} 个位置点\n※ 数据来源于米游社wiki"

    return mes



def get_resource_list_mes():

    temp = {}

    for id in data["all_resource_type"].keys():
        # 先找1级目录
        if data["all_resource_type"][id]["depth"] == 1:
            temp[id] = []

    for id in data["all_resource_type"].keys():
        # 再找2级目录
        if data["all_resource_type"][id]["depth"] == 2:
            temp[str(data["all_resource_type"][id]["parent_id"])].append(id)

    mes = "当前资源列表如下：\n"

    for resource_type_id in temp.keys():

        if resource_type_id in ["1","12","50","51","95","131"]:
            # 在游戏里能查到的数据这里就不列举了，不然消息太长了
            continue

        mes += f"{data['all_resource_type'][resource_type_id]['name']}："
        for resource_id in temp[resource_type_id]:
            mes += f"{data['all_resource_type'][resource_id]['name']}，"
        mes += "\n"

    return mes
