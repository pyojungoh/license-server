package com.hanjin.models

/**
 * 로그인 응답 모델
 */
data class LoginResponse(
    val success: Boolean,
    val message: String,
    val access_token: String? = null,
    val expires_at: String? = null,
    val user_info: UserInfo? = null,
    val code: String? = null  // 에러 코드 (예: "DEVICE_MISMATCH")
)

data class UserInfo(
    val user_id: String,
    val name: String,
    val email: String?,
    val expiry_date: String?,
    val is_active: Boolean
)





