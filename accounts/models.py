from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """Extended profile for User, storing last login IP, location and role."""
    class Role(models.TextChoices):
        USER = 'user', 'User'
        ADMIN = 'admin', 'Admin'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(
        max_length=10, choices=Role.choices, default=Role.USER, verbose_name='Role'
    )
    last_login_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='Last Login IP')
    last_login_location = models.CharField(max_length=255, null=True, blank=True, verbose_name='Last Login Location')

    def __str__(self):
        return f'{self.user.username} — {self.role}'

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'


class Post(models.Model):
    """A blog post by a user."""
    title = models.CharField(max_length=200, verbose_name='Title')
    content = models.TextField(verbose_name='Content')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'


class Comment(models.Model):
    """A comment on a post, supports nested replies and voice messages."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.TextField(max_length=2000, blank=True, verbose_name='Content')
    audio = models.FileField(upload_to='comments/audio/', null=True, blank=True, verbose_name='Voice Message')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')

    def __str__(self):
        return f'{self.author.username} on {self.post.title[:30]}'

    @property
    def has_audio(self):
        return bool(self.audio)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'


class BodyMeasurement(models.Model):
    """A single body composition measurement record from a smart scale."""
    measured_at = models.DateTimeField(verbose_name='测量时间')
    
    # Core metrics
    weight_jin = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='体重(斤)')
    bmi = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='BMI')
    body_fat_pct = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='体脂率(%)')
    body_fat_score = models.IntegerField(null=True, blank=True, verbose_name='体脂得分')
    
    # Muscle & fat
    skeletal_muscle_jin = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='骨骼肌量(斤)')
    visceral_fat_level = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True, verbose_name='内脏脂肪等级')
    arms_legs_muscle_index = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='四肢骨骼肌指数(kg/m²)')
    waist_hip_ratio = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name='推测腰臀比')
    
    # Body composition
    body_water_pct = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='水分率(%)')
    protein_pct = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='蛋白质(%)')
    bone_mineral_jin = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name='骨盐量(斤)')
    fat_free_mass_jin = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='去脂体重(斤)')
    
    # Vital signs
    basal_metabolism_kcal = models.IntegerField(null=True, blank=True, verbose_name='基础代谢(千卡/日)')
    body_age = models.IntegerField(null=True, blank=True, verbose_name='身体年龄')
    heart_rate = models.IntegerField(null=True, blank=True, verbose_name='心率(次/分)')
    
    # Body type info
    body_type = models.CharField(max_length=50, null=True, blank=True, verbose_name='体型类型')
    body_shape = models.CharField(max_length=50, null=True, blank=True, verbose_name='体形态')
    
    # Changes from previous measurement
    bmi_change = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='BMI变化')
    body_fat_change = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='体脂率变化(%)')
    skeletal_muscle_change = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='骨骼肌变化(斤)')
    body_water_change = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='水分率变化(%)')
    fat_free_mass_change = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='去脂体重变化(斤)')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='记录创建时间')

    def __str__(self):
        w = self.weight_jin or '?'
        b = self.bmi or '?'
        return f'体重 {w}斤 (BMI {b}) — {self.measured_at.strftime("%Y-%m-%d %H:%M")}'

    class Meta:
        ordering = ['-measured_at']
        verbose_name = '体重测量'
        verbose_name_plural = '体重测量数据'
