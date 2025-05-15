from xmindparser import xmind_to_dict, config
import json
import os

class XmindGenerator:
    def __init__(self):
        self.data = {
            'topic': {
                'title': '',
                'topics': []
            }
        }

    def create_mindmap(self, title, content_dict):
        try:
            # 设置根节点标题
            self.data['topic']['title'] = title
            
            # 转换内容为 XMind 格式
            self._convert_to_topics(content_dict, self.data['topic']['topics'])
            
            # 保存为 JSON 文件（临时）
            temp_json = f"{title}_temp.json"
            with open(temp_json, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            
            # 转换为 XMind 文件
            output_file = f"{title}.xmind"
            config.set_logger(False)  # 关闭日志输出
            xmind_to_dict(temp_json, output_file)
            
            # 删除临时 JSON 文件
            os.remove(temp_json)
            
            print(f"思维导图已保存为: {os.path.abspath(output_file)}")
            return output_file
            
        except Exception as e:
            raise Exception(f"创建思维导图失败: {str(e)}")

    def _convert_to_topics(self, content, topics_list):
        if isinstance(content, dict):
            for key, value in content.items():
                topic = {'title': str(key), 'topics': []}
                self._convert_to_topics(value, topic['topics'])
                topics_list.append(topic)
        elif isinstance(content, list):
            for item in content:
                topic = {'title': str(item)}
                topics_list.append(topic)
        else:
            topic = {'title': str(content)}
            topics_list.append(topic)