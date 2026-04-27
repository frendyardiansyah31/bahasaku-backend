"""
Serializers untuk authentication.

Tanggung jawab file ini:
  - Validasi format dan isi input dari request
  - Serialisasi data user untuk response

Tidak ada business logic atau DB write di sini — hanya validasi input dan output.
"""

from rest_framework import serializers

from .models import User


class RegisterSerializer(serializers.Serializer):
    # name = serializers.CharField(max_length=255)
    # email = serializers.EmailField()
    # password = serializers.CharField(min_length=8, write_only=True)
    # password_confirm = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email sudah terdaftar')
        return value

    def validate(self, data):
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError('Password dan konfirmasi password tidak cocok')
        return data

    # def create(self, validated_data):
    #     first = validated_data.pop('first_name')
    #     last = validated_data.pop('last_name')
    #     validated_data.pop('password_confirm')

    #     user = User.objects.create_user(
    #         name=name,
    #         **validated_data
    #     )
    #     return user
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'is_onboarded']
