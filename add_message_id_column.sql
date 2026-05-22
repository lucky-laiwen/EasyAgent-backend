-- 添加 message_id 字段到 knowledge_document 表
ALTER TABLE knowledge_document 
ADD COLUMN message_id BIGINT NULL COMMENT 'NULL=未绑定消息, 非NULL=绑定到具体消息';

-- 添加外键约束
ALTER TABLE knowledge_document 
ADD CONSTRAINT fk_knowledge_document_message 
FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE;

-- 添加索引
CREATE INDEX idx_knowledge_document_message_id ON knowledge_document(message_id);
