# Honkai_Starrail_bot
星穹铁路资源查询

## 简介

这个插件帮助群员在QQ群内查询星穹铁路的资源位点。
其他功能正在开发中。欢迎PR


## **部署**
1. 在HoshinoBot/hoshino/modules 目录下拉取本项目
```
git clone https://github.com/Cathgao/Honkai_Starrail_bot
```

2. 在hoshino/config/\_\_bot\_\_.py文件中，MODULES_ON里添加 "Honkai_Starrail_bot"

3. 手动在hoshino\modules\Honkai_Starrail_bot\query_resource_points中创建文件夹maps 否则会路径报错

## **使用**

群聊中发送 `#哪里有[资源名称]` ，如 `#哪里有普通战利品`

发送 `星铁资源列表` 获取可查询的资源名称

## 鸣谢 
[Genshin_Impact_bot](https://github.com/H-K-Y/Genshin_Impact_bot)
