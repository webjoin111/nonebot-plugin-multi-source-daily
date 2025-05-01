# 多源日报 / Multi-Source Daily

<div align="center">

# 多源日报 (Multi-Source Daily)

_✨ 一个聚合多种日报源的NoneBot2插件，支持定时发送和多API源 ✨_

</div>

## 📖 介绍

多源日报是一个基于 [NoneBot2](https://github.com/nonebot/nonebot2) 的插件，提供多种日报信息的聚合服务，包括60秒看世界、知乎日报、IT之家日报、摸鱼日报、历史上的今天等。插件支持多API源自动切换，确保服务的稳定性，同时提供定时发送功能，让您的群聊每天都能自动获取最新资讯。

## 💿 安装

### 使用 nb-cli 安装（推荐）

```bash
nb plugin install nonebot-plugin-multi-source-daily
```

### 使用 pip 安装

```bash
pip install nonebot-plugin-multi-source-daily
```

### 手动安装

```bash
git clone https://github.com/yourusername/nonebot-plugin-multi-source-daily.git
cd nonebot-plugin-multi-source-daily
pip install .
```

## ⚙️ 配置

在 NoneBot2 全局配置文件中添加以下配置：

```dotenv
# config.env
# 插件配置项
MULTI_SOURCE_DAILY_CACHE_TTL=3600  # 缓存有效期（秒）
MULTI_SOURCE_DAILY_API_TIMEOUT=10  # API请求超时时间（秒）
MULTI_SOURCE_DAILY_RETRY_TIMES=3   # API请求重试次数
```

## 🎉 使用

### 基础命令

```
日报 [类型] [-f 格式]
  - 获取指定类型的日报信息
  - 可选格式: image(图片), text(文字)
  - 例如: 日报 60s -f text
  - 例如: 日报 历史上的今天

日报详情 [类型] [数字]
  - 获取指定日报类型中特定序号新闻的网页截图
  - 例如: 日报详情 IT 3
  - 仅对有网页链接的日报类型有效

[数字]
  - 回复日报图片并发送数字，获取对应序号新闻的网页截图
  - 例如: 回复IT之家日报图片 + 5
  - 仅对有网页链接的日报类型有效
```

### 定时日报命令

```
定时日报 设置 [类型] [HH:MM或HHMM] [-g 群号] [-all] [-f 格式]
  - 设置定时发送指定类型的日报(仅限超级用户)
  - -g 参数可指定特定群号
  - -all 参数将对所有群生效
  - -f 参数可设置格式(image/text)
  - 例如: 定时日报 设置 60s 08:00 -g 123456 -f text
  - 例如: 定时日报 设置 知乎 09:30 -all

定时日报 取消 [类型] [-g 群号] [-all]
  - 取消本群或指定群的定时日报(仅限超级用户)
  - 例如: 定时日报 取消 60s -g 123456

定时日报 查看 [-g 群号] [-all] [-t]
  - 查看当前群的日报订阅情况
  - -g 和 -all 参数仅限超级用户使用
  - -t 使用文本方式显示，默认为图片
  - 例如: 定时日报 查看 -all -t

定时日报 修复 [-a]
  - 修复日报系统，重新加载定时任务配置
  - -a 参数将重置所有定时任务配置
```

### API源管理命令

```
日报API [-t]
  - 查看所有日报API源及其状态
  - -t 使用文本方式显示，默认为图片

日报API 启用 [类型] [序号]
  - 启用指定的日报API源
  - 例如: 日报API 启用 知乎 2

日报API 禁用 [类型] [序号]
  - 禁用指定的日报API源
  - 例如: 日报API 禁用 知乎 2

日报API 重置 [类型]
  - 重置指定日报类型的API源状态
  - 类型可以是: 60s, 知乎, moyu, ithome, 历史上的今天, all
  - 例如: 日报API 重置 知乎

日报API 重置 -a
  - 重置所有API源状态
  - 当所有日报来源均不可用时使用
```

### 其他命令

```
日报列表
  - 显示所有支持的日报类型
```

## 🙏 鸣谢

- [NoneBot2](https://github.com/nonebot/nonebot2)：优秀的聊天机器人框架
- [go-cqhttp](https://github.com/Mrs4s/go-cqhttp)：稳定可靠的 CQHTTP 实现

## 📄 开源许可

本项目采用 [MIT](./LICENSE) 许可证开源。

```

Copyright (c) 2023 Your Name

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
