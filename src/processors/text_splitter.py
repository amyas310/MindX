class TextSplitter:
    """按时间线分割文本，保证句子完整性"""
    
    def __init__(self):
        self.cache_dir = config.CACHE_DIR / "text_splits"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def split_by_time(self, segments, audio_duration):
        """按时间线分割文本
        
        参数:
            segments: 带时间戳的文本片段列表 [{"text":str, "start":float, "end":float}]
            audio_duration: 音频总时长(秒)
        返回:
            分割后的文本块列表
        """
        if not segments or audio_duration <= 0:
            return []
            
        # 计算需要分割的段数（每15分钟一段，至少1段）
        num_chunks = max(1, int(audio_duration / (15 * 60)))
        chunk_duration = audio_duration / num_chunks
        
        chunks = []
        current_chunk = []
        current_end = chunk_duration
        
        for seg in segments:
            if seg["end"] > current_end and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [seg["text"]]
                current_end += chunk_duration
            else:
                current_chunk.append(seg["text"])
        
        # 添加最后一块
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks

    def split_by_length(self, text, max_length=10000):
        """按长度分割文本，保证句子完整性
        
        参数:
            text: 要分割的文本
            max_length: 每个块的最大字符数，默认10000字
        返回:
            分割后的文本块列表
        """
        if not text or len(text) <= max_length:
            return [text]
            
        # 按句号和换行符分割
        sentences = []
        for paragraph in text.split("\n"):
            if not paragraph.strip():
                continue
            for sent in paragraph.split("。"):
                if sent.strip():
                    sentences.append(sent.strip() + "。")
                    
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # 如果单个句子就超过了最大长度，强制分割
            if len(sentence) > max_length:
                if current_chunk:
                    chunks.append(current_chunk)
                # 按max_length大小强制分割长句子
                for i in range(0, len(sentence), max_length):
                    chunks.append(sentence[i:i + max_length])
                current_chunk = ""
                continue
                
            # 如果当前块加上新句子超过最大长度，保存当前块并开始新块
            if len(current_chunk) + len(sentence) > max_length and current_chunk:
                chunks.append(current_chunk)
                current_chunk = sentence
            else:
                current_chunk += sentence
                
        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks