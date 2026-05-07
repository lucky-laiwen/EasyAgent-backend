-- ============================================
-- 数据库迁移脚本：创建 tool_calls 表并同步 messages 表
-- 功能：将 messages 表中的工具字段迁移到独立的 tool_calls 表
-- 执行前请备份数据库！
-- ============================================

-- 1. 创建 tool_calls 表
CREATE TABLE IF NOT EXISTS `tool_calls` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `message_id` BIGINT NOT NULL,
    `tool_name` VARCHAR(100) NOT NULL COMMENT '工具名称',
    `tool_content` TEXT COMMENT '工具返回结果',
    `tool_input` TEXT COMMENT '工具输入参数',
    `status` INT DEFAULT 1 COMMENT '状态: 1=成功, 0=失败',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_message_id` (`message_id`),
    FOREIGN KEY (`message_id`) REFERENCES `messages`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 从 messages 表迁移现有数据到 tool_calls 表
INSERT INTO `tool_calls` (`message_id`, `tool_name`, `tool_content`, `status`)
SELECT
    `id`,
    `tool_name`,
    `tool_content`,
    1
FROM `messages`
WHERE `tool_name` IS NOT NULL
  AND `tool_name` != '';

-- 3. 删除 messages 表中的旧字段
ALTER TABLE `messages` DROP COLUMN `tool_name`;
ALTER TABLE `messages` DROP COLUMN `tool_content`;

-- ============================================
-- 迁移完成后的 messages 表结构：
-- ============================================
-- CREATE TABLE messages (
--     id            BIGINT AUTO_INCREMENT PRIMARY KEY,
--     chat_id       INT NOT NULL,
--     sender        TINYINT NOT NULL COMMENT '0=user, 1=ai',
--     content       TEXT NOT NULL,
--     created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
--     think_content TEXT,
--     FOREIGN KEY (chat_id) REFERENCES chat(id) ON DELETE CASCADE
-- );
-- ============================================

-- ============================================
-- 回滚脚本（如需撤销迁移）
-- ============================================
-- ALTER TABLE `messages` ADD COLUMN `tool_content` TEXT;
-- ALTER TABLE `messages` ADD COLUMN `tool_name` CHAR(50);
--
-- UPDATE `messages` m
-- JOIN `tool_calls` tc ON m.id = tc.message_id
-- SET m.tool_name = tc.tool_name, m.tool_content = tc.tool_content;
--
-- DROP TABLE IF EXISTS `tool_calls`;
