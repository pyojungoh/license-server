package com.hanjin

import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.util.Log
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.hanjin.api.ApiClient
import com.hanjin.models.LoginRequest
import com.hanjin.models.LoginResponse
import com.hanjin.utils.DeviceUtils
import kotlinx.coroutines.launch

class LoginActivity : AppCompatActivity() {
    
    private lateinit var etUserId: EditText
    private lateinit var etPassword: EditText
    private lateinit var btnLogin: Button
    
    private val prefs: SharedPreferences by lazy {
        getSharedPreferences("hanjin_prefs", Context.MODE_PRIVATE)
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)
        
        // 로그인 상태 확인
        if (isLoggedIn()) {
            // 이미 로그인되어 있으면 메인 화면으로 이동
            startActivity(Intent(this, MainActivity::class.java))
            finish()
            return
        }
        
        // UI 초기화
        etUserId = findViewById(R.id.etUserId)
        etPassword = findViewById(R.id.etPassword)
        btnLogin = findViewById(R.id.btnLogin)
        
        btnLogin.setOnClickListener {
            attemptLogin()
        }
    }
    
    private fun attemptLogin() {
        val userId = etUserId.text.toString().trim()
        val password = etPassword.text.toString()
        
        // 입력 검증
        if (userId.isEmpty()) {
            etUserId.error = "아이디를 입력하세요"
            return
        }
        
        if (password.isEmpty()) {
            etPassword.error = "비밀번호를 입력하세요"
            return
        }
        
        // 로그인 버튼 비활성화
        btnLogin.isEnabled = false
        btnLogin.text = "로그인 중..."
        
        // 기기 UUID 가져오기
        val deviceUuid = DeviceUtils.getDeviceUUID(this)
        val deviceName = android.os.Build.MODEL // 기기 모델명
        
        // 로그인 요청
        lifecycleScope.launch {
            try {
                val request = LoginRequest(
                    user_id = userId,
                    password = password,
                    device_uuid = deviceUuid,
                    device_name = deviceName
                )
                
                val response = ApiClient.apiService.login(request)
                
                Log.d("LoginActivity", "서버 응답: success=${response.success}, token=${if (response.access_token != null) "있음 (${response.access_token?.take(20)}...)" else "없음"}")
                Log.d("LoginActivity", "응답 메시지: ${response.message}")
                Log.d("LoginActivity", "응답 전체: success=${response.success}, message=${response.message}, access_token=${response.access_token}, expires_at=${response.expires_at}")
                
                runOnUiThread {
                    if (response.success && response.access_token != null) {
                        // 로그인 성공
                        Log.d("LoginActivity", "로그인 성공 - 토큰 저장 및 MainActivity 이동 시작")
                        val expiryDate = response.user_info?.expiry_date
                        saveLoginInfo(response.access_token!!, userId, response.expires_at, expiryDate)
                        Toast.makeText(this@LoginActivity, "로그인 성공! MainActivity로 이동", Toast.LENGTH_SHORT).show()
                        
                        // 메인 화면으로 이동
                        try {
                            val intent = Intent(this@LoginActivity, MainActivity::class.java)
                            intent.putExtra("access_token", response.access_token)
                            Log.d("LoginActivity", "Intent 생성 완료 - startActivity 호출")
                            startActivity(intent)
                            Log.d("LoginActivity", "startActivity 완료 - finish 호출")
                            finish()
                        } catch (e: Exception) {
                            Log.e("LoginActivity", "MainActivity 이동 실패", e)
                            Toast.makeText(this@LoginActivity, "화면 이동 오류: ${e.message}", Toast.LENGTH_LONG).show()
                        }
                    } else {
                        // 로그인 실패
                        Log.d("LoginActivity", "로그인 실패 - success=${response.success}, code=${response.code}")
                        handleLoginError(response)
                        btnLogin.isEnabled = true
                        btnLogin.text = "로그인"
                    }
                }
            } catch (e: Exception) {
                // 네트워크 오류 등
                e.printStackTrace()
                runOnUiThread {
                    Toast.makeText(
                        this@LoginActivity,
                        "로그인 실패: ${e.message}",
                        Toast.LENGTH_LONG
                    ).show()
                    btnLogin.isEnabled = true
                    btnLogin.text = "로그인"
                }
            }
        }
    }
    
    private fun handleLoginError(response: LoginResponse) {
        when (response.code) {
            "DEVICE_MISMATCH" -> {
                Toast.makeText(
                    this,
                    "등록된 기기가 아닙니다.\n다른 기기에서 로그인할 수 없습니다.",
                    Toast.LENGTH_LONG
                ).show()
            }
            else -> {
                Toast.makeText(
                    this,
                    response.message ?: "로그인 실패",
                    Toast.LENGTH_SHORT
                ).show()
            }
        }
    }
    
    private fun saveLoginInfo(token: String, userId: String, expiresAt: String?, expiryDate: String?) {
        prefs.edit()
            .putString("access_token", token)
            .putString("user_id", userId)
            .putString("expires_at", expiresAt)
            .putString("expiry_date", expiryDate)
            .putBoolean("is_logged_in", true)
            .apply()
    }
    
    private fun isLoggedIn(): Boolean {
        return prefs.getBoolean("is_logged_in", false) &&
                prefs.getString("access_token", null) != null
    }
}

