<template>
  <div>
    <h1 class="page-title">创建 Skill 指南</h1>
    <p class="page-subtitle">Skill 内容由 Git 管理，元数据自动同步到数据库。以下是创建和更新 Skill 的流程。</p>

    <div class="card" style="max-width: 700px">
      <h3>创建新 Skill</h3>
      <ol style="line-height: 2">
        <li>在项目根目录的 <code>skills/</code> 下创建子目录：<code>mkdir -p skills/your-skill-name</code></li>
        <li>创建 <code>skills/your-skill-name/skill.yaml</code>：</li>
      </ol>
      <pre style="background: #f5f5f5; padding: 1rem; border-radius: 6px; font-size: 0.85rem">
name: your-skill-name
description: 技能描述
tags: [tag1, tag2]
version: 1.0.0</pre>

      <ol start="3" style="line-height: 2">
        <li>创建 <code>skills/your-skill-name/prompt.md</code>，写入 Markdown 指令内容</li>
        <li>（可选）添加扩展文件到子目录：<code>examples/</code>、<code>rules/</code> 等</li>
        <li>执行 <code>git add skills/your-skill-name && git commit -m "feat: add skill"</code></li>
        <li>运行 <code>agent-platform skill-sync</code> 同步到数据库</li>
      </ol>
    </div>

    <div class="card" style="max-width: 700px; margin-top: 1rem">
      <h3>编辑已有 Skill</h3>
      <ul style="line-height: 2">
        <li><strong>修改 prompt：</strong>在 IDE 中编辑 <code>skills/&lt;name&gt;/prompt.md</code>，或在前端列表页点击"编辑 Prompt"</li>
        <li><strong>修改元数据：</strong>编辑 <code>skill.yaml</code> 中的 description/tags/version</li>
        <li><strong>添加扩展文件：</strong>在 <code>skills/&lt;name&gt;/examples/</code> 下创建 <code>*.md</code> 文件</li>
        <li>修改后执行 <code>git commit</code> + <code>agent-platform skill-sync</code></li>
      </ul>
    </div>

    <div class="card" style="max-width: 700px; margin-top: 1rem">
      <h3>版本管理</h3>
      <ul style="line-height: 2">
        <li>每次 <code>git commit</code> 后，Skill 的内容版本自动由 Git 管理</li>
        <li>查看历史：<code>git log skills/&lt;name&gt;/prompt.md</code></li>
        <li>回滚：<code>git checkout &lt;hash&gt; -- skills/&lt;name&gt;/</code></li>
      </ul>
    </div>

    <div style="margin-top: 1.5rem">
      <router-link to="/skills" class="btn btn-outline">← 返回列表</router-link>
    </div>
  </div>
</template>
