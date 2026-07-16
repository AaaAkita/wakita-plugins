"""
Django 迁移模板 — 幂等 schema 收敛

将此文件复制到 app/migrations/ 目录，修改：
- 类名
- operations 中的表名和列名
"""

from django.db import migrations, models


def add_column_if_not_exists(apps, schema_editor):
    """幂等地添加列（如果不存在）"""
    # 获取模型
    User = apps.get_model('app', 'User')
    
    # 检查列是否已存在
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'app_user'
              AND column_name = 'avatar'
        """)
        exists = cursor.fetchone()[0] > 0
    
    if not exists:
        # 添加列
        schema_editor.add_field(
            User,
            models.CharField(max_length=255, null=True, blank=True),
        )


def remove_column_if_exists(apps, schema_editor):
    """幂等地移除列（如果存在）"""
    User = apps.get_model('app', 'User')
    
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'app_user'
              AND column_name = 'avatar'
        """)
        exists = cursor.fetchone()[0] > 0
    
    if exists:
        schema_editor.remove_field(
            User,
            User._meta.get_field('avatar'),
        )


class Migration(migrations.Migration):
    dependencies = [
        ('app', '0001_initial'),  # 修改为上一个 migration
    ]

    operations = [
        migrations.RunPython(
            add_column_if_not_exists,
            remove_column_if_exists,
        ),
    ]

"""
使用方法：
1. 生成 migration：python manage.py makemigrations
2. 运行迁移：python manage.py migrate
3. 回滚迁移：python manage.py migrate app 0001
"""