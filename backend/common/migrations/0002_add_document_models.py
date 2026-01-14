# Generated manually for pluggable document datastore implementation

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0001_add_config_data_model"),
    ]

    operations = [
        migrations.CreateModel(
            name="DownloadQueueItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "doc_id",
                    models.CharField(db_index=True, max_length=255, unique=True),
                ),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Download Queue Item",
                "verbose_name_plural": "Download Queue Items",
                "db_table": "download_queue_item",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="VideoDocument",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "doc_id",
                    models.CharField(db_index=True, max_length=255, unique=True),
                ),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Video Document",
                "verbose_name_plural": "Video Documents",
                "db_table": "video_document",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ChannelDocument",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "doc_id",
                    models.CharField(db_index=True, max_length=255, unique=True),
                ),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Channel Document",
                "verbose_name_plural": "Channel Documents",
                "db_table": "channel_document",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="PlaylistDocument",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "doc_id",
                    models.CharField(db_index=True, max_length=255, unique=True),
                ),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Playlist Document",
                "verbose_name_plural": "Playlist Documents",
                "db_table": "playlist_document",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="CommentDocument",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "doc_id",
                    models.CharField(db_index=True, max_length=255, unique=True),
                ),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Comment Document",
                "verbose_name_plural": "Comment Documents",
                "db_table": "comment_document",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SubtitleDocument",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "doc_id",
                    models.CharField(db_index=True, max_length=255, unique=True),
                ),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Subtitle Document",
                "verbose_name_plural": "Subtitle Documents",
                "db_table": "subtitle_document",
                "ordering": ["-created_at"],
            },
        ),
    ]
