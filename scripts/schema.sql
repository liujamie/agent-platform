-- ============================================
-- Agent Platform — 数据库初始化脚本
-- 适用数据库: MySQL 8.0+
-- ============================================

CREATE DATABASE IF NOT EXISTS agent_platform
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE agent_platform;

-- ============================================
-- Agent 定义表
-- ============================================
CREATE TABLE IF NOT EXISTS `agent_definitions` (
  `id`              INT           NOT NULL AUTO_INCREMENT,
  `name`            VARCHAR(100)  NOT NULL COMMENT 'Agent 名称',
  `role`            TEXT          NOT NULL COMMENT 'System prompt',
  `model_name`      VARCHAR(50)   NOT NULL COMMENT '模型名',
  `tools`           JSON          DEFAULT NULL COMMENT '绑定的工具列表',
  `connections`     JSON          DEFAULT NULL COMMENT '绑定的 MCP 连接列表',
  `skills`          JSON          DEFAULT NULL COMMENT '绑定的 Skill 名称列表',
  `memory_enabled`  TINYINT(1)    DEFAULT 1,
  `temperature`     INT           DEFAULT 70 COMMENT '0-100 缩放值',
  `status`          VARCHAR(20)   DEFAULT 'active' COMMENT 'active / archived',
  `created_at`      DATETIME      DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- Workflow 定义表
-- ============================================
CREATE TABLE IF NOT EXISTS `workflow_definitions` (
  `id`              INT           NOT NULL AUTO_INCREMENT,
  `name`            VARCHAR(100)  NOT NULL COMMENT 'Workflow 名称',
  `description`     TEXT          DEFAULT NULL,
  `definition`      JSON          NOT NULL COMMENT 'nodes + edges',
  `status`          VARCHAR(20)   DEFAULT 'active' COMMENT 'active / archived',
  `created_at`      DATETIME      DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 运行日志表
-- ============================================
CREATE TABLE IF NOT EXISTS `run_logs` (
  `id`              INT           NOT NULL AUTO_INCREMENT,
  `trace_id`        VARCHAR(36)   NOT NULL,
  `agent_id`        INT           DEFAULT NULL,
  `workflow_id`     INT           DEFAULT NULL,
  `input`           TEXT          DEFAULT NULL,
  `output`          TEXT          DEFAULT NULL,
  `status`          VARCHAR(20)   DEFAULT 'success' COMMENT 'success / error',
  `tokens`          INT           DEFAULT 0,
  `duration_ms`     INT           DEFAULT 0,
  `created_at`      DATETIME      DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `ix_run_logs_trace_id` (`trace_id`),
  INDEX `idx_run_logs_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 模型配置表
-- ============================================
CREATE TABLE IF NOT EXISTS `model_configs` (
  `id`                INT           NOT NULL AUTO_INCREMENT,
  `name`              VARCHAR(100)  NOT NULL COMMENT '模型标识名',
  `provider`          VARCHAR(20)   NOT NULL DEFAULT 'openai' COMMENT 'openai / dashscope',
  `api_key_encrypted` TEXT          DEFAULT NULL COMMENT '加密后的 API Key',
  `base_url`          VARCHAR(255)  DEFAULT NULL COMMENT 'API 地址（仅 openai 类型）',
  `model`             VARCHAR(100)  NOT NULL COMMENT '模型名，如 deepseek-v4-flash',
  `is_current`        TINYINT(1)    DEFAULT 0 COMMENT '是否为当前使用的模型',
  `created_at`        DATETIME      DEFAULT CURRENT_TIMESTAMP,
  `updated_at`        DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- MCP 连接配置表
-- ============================================
CREATE TABLE IF NOT EXISTS `mcp_connections` (
  `id`              INT           NOT NULL AUTO_INCREMENT,
  `name`            VARCHAR(100)  NOT NULL COMMENT '连接名称',
  `connection_type` VARCHAR(20)   NOT NULL DEFAULT 'stdio' COMMENT 'stdio / sse',
  `command`         VARCHAR(255)  DEFAULT NULL COMMENT 'stdio 模式：启动命令',
  `args`            JSON          DEFAULT NULL COMMENT 'stdio 模式：命令参数列表',
  `url`             VARCHAR(255)  DEFAULT NULL COMMENT 'SSE 模式：服务器 URL',
  `env_vars`        JSON          DEFAULT NULL COMMENT '环境变量键值对',
  `status`          VARCHAR(20)   DEFAULT 'disconnected' COMMENT 'disconnected / connected / error',
  `error_message`   TEXT          DEFAULT NULL COMMENT '连接失败时的错误信息',
  `created_at`      DATETIME      DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_mcp_connections_name` (`name`),
  INDEX `idx_mcp_connections_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- Skill 定义表（元数据层，内容存储在 skills/*/ 文件系统）
-- ============================================
CREATE TABLE IF NOT EXISTS `skill_definitions` (
  `id`              INT           NOT NULL AUTO_INCREMENT,
  `name`            VARCHAR(100)  NOT NULL COMMENT '技能名称（=目录名）',
  `description`     TEXT          DEFAULT NULL COMMENT '简要描述',
  `tags`            JSON          DEFAULT NULL COMMENT '标签列表',
  `path`            VARCHAR(255)  NOT NULL COMMENT 'skills/{name} 相对路径',
  `version`         VARCHAR(20)   DEFAULT '1.0.0' COMMENT '语义版本号',
  `git_commit_hash` VARCHAR(40)   DEFAULT NULL COMMENT '最近一次同步的 Git commit',
  `status`          VARCHAR(20)   DEFAULT 'active' COMMENT 'active / archived',
  `created_at`      DATETIME      DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_skill_definitions_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 会话记录表（Conversation — 完整消息永久存储）
-- ============================================
CREATE TABLE IF NOT EXISTS `conversations` (
  `id`              INT           NOT NULL AUTO_INCREMENT,
  `session_id`      VARCHAR(100)  NOT NULL COMMENT '前端传入的会话标识',
  `agent_id`        INT           NOT NULL COMMENT '所属 Agent ID',
  `name`            VARCHAR(200)  DEFAULT '新对话' COMMENT '会话名称',
  `message_count`   INT           DEFAULT 0 COMMENT '消息总数',
  `status`          VARCHAR(20)   DEFAULT 'active' COMMENT 'active / archived',
  `created_at`      DATETIME      DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_conversations_session` (`session_id`),
  INDEX `idx_conversations_agent` (`agent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 会话消息表（ConversationMessage — 每条消息一条记录）
-- ============================================
CREATE TABLE IF NOT EXISTS `conversation_messages` (
  `id`              INT           NOT NULL AUTO_INCREMENT,
  `conversation_id` INT           NOT NULL COMMENT '关联 conversations.id',
  `role`            VARCHAR(20)   NOT NULL COMMENT 'user / assistant / tool / system',
  `content`         TEXT          NOT NULL COMMENT '消息内容。超长文本后续可存入 OSS，此字段存路径',
  `tokens`          INT           DEFAULT 0 COMMENT '预估 token 数',
  `msg_index`       INT           NOT NULL COMMENT '消息序号（从 0 开始）',
  `created_at`      DATETIME      DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_conv_msg_conv` (`conversation_id`, `msg_index`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
