package com.hanjin.models

/**
 * 로그인 요청 모델
 */
data class LoginRequest(
    val user_id: String,
    val password: String,
    val device_uuid: String,
    val device_name: String? = null
)








