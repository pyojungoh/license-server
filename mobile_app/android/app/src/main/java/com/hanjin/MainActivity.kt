package com.hanjin

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.util.Log
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.hanjin.ble.BLEService
import java.text.SimpleDateFormat
import java.util.*

class MainActivity : AppCompatActivity() {
    
    private lateinit var tvStatus: TextView
    private lateinit var tvUserInfo: TextView
    private lateinit var btnScan: Button
    private lateinit var btnSendToken: Button
    private lateinit var btnLogout: Button
    
    private var accessToken: String? = null
    private var bluetoothAdapter: BluetoothAdapter? = null
    private var bleService: BLEService? = null
    private var isConnected = false
    
    private val REQUEST_BLUETOOTH_PERMISSIONS = 100
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Log.d("MainActivity", "onCreate 시작")
        setContentView(R.layout.activity_main)
        Log.d("MainActivity", "setContentView 완료")
        Toast.makeText(this, "MainActivity 시작됨", Toast.LENGTH_SHORT).show()
        
        // 토큰 가져오기
        val tokenFromIntent = intent.getStringExtra("access_token")
        Log.d("MainActivity", "Intent에서 토큰: ${if (tokenFromIntent != null) "있음" else "없음"}")
        
        val tokenFromPrefs = getSharedPreferences("hanjin_prefs", Context.MODE_PRIVATE)
            .getString("access_token", null)
        Log.d("MainActivity", "SharedPreferences에서 토큰: ${if (tokenFromPrefs != null) "있음" else "없음"}")
        
        accessToken = tokenFromIntent ?: tokenFromPrefs
        
        if (accessToken == null) {
            Log.e("MainActivity", "토큰이 없음 - LoginActivity로 이동")
            Toast.makeText(this, "로그인이 필요합니다", Toast.LENGTH_SHORT).show()
            val loginIntent = Intent(this, LoginActivity::class.java)
            startActivity(loginIntent)
            finish()
            return
        }
        
        Log.d("MainActivity", "토큰 확인 완료 - UI 초기화 시작")
        
        // UI 초기화
        tvStatus = findViewById(R.id.tvStatus)
        tvUserInfo = findViewById(R.id.tvUserInfo)
        btnScan = findViewById(R.id.btnScan)
        btnSendToken = findViewById(R.id.btnSendToken)
        btnLogout = findViewById(R.id.btnLogout)
        
        // 사용자 정보 표시
        displayUserInfo()
        
        // 블루투스 어댑터 초기화
        val bluetoothManager = getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        bluetoothAdapter = bluetoothManager.adapter
        
        // BLE 서비스 초기화
        bleService = BLEService(this).apply {
            onDeviceFound = { device ->
                runOnUiThread {
                    updateStatus("ESP32 장치 발견: ${device.name}\n연결 중...")
                    connect()
                }
            }
            onConnected = {
                runOnUiThread {
                    isConnected = true
                    updateStatus("ESP32 연결됨\n토큰 전송 가능")
                    btnSendToken.isEnabled = true
                }
            }
            onDisconnected = {
                runOnUiThread {
                    isConnected = false
                    updateStatus("ESP32 연결 끊김")
                    btnSendToken.isEnabled = false
                }
            }
            onTokenSent = { success ->
                runOnUiThread {
                    if (success) {
                        updateStatus("토큰 전송 성공!\nESP32 인증 완료")
                        Toast.makeText(this@MainActivity, "토큰 전송 성공", Toast.LENGTH_SHORT).show()
                        // 토큰 전송 성공 시 유효시간 업데이트
                        displayUserInfo()
                    } else {
                        updateStatus("토큰 전송 실패")
                        Toast.makeText(this@MainActivity, "토큰 전송 실패", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        }
        
        // 블루투스 권한 확인
        checkBluetoothPermissions()
        
        btnScan.setOnClickListener {
            if (checkBluetoothPermissions()) {
                startBLEScan()
            }
        }
        
        btnSendToken.setOnClickListener {
            if (checkBluetoothPermissions()) {
                sendTokenToESP32()
            }
        }
        
        btnLogout.setOnClickListener {
            logout()
        }
        
        updateStatus("ESP32 장치를 검색하세요")
    }
    
    private fun checkBluetoothPermissions(): Boolean {
        val permissions = mutableListOf<String>()
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            // Android 12 이상
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_SCAN)
                != PackageManager.PERMISSION_GRANTED) {
                permissions.add(Manifest.permission.BLUETOOTH_SCAN)
            }
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT)
                != PackageManager.PERMISSION_GRANTED) {
                permissions.add(Manifest.permission.BLUETOOTH_CONNECT)
            }
        } else {
            // Android 11 이하
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
                != PackageManager.PERMISSION_GRANTED) {
                permissions.add(Manifest.permission.ACCESS_FINE_LOCATION)
            }
        }
        
        if (permissions.isNotEmpty()) {
            ActivityCompat.requestPermissions(
                this,
                permissions.toTypedArray(),
                REQUEST_BLUETOOTH_PERMISSIONS
            )
            return false
        }
        
        return true
    }
    
    private fun startBLEScan() {
        if (!isBluetoothEnabled()) {
            Toast.makeText(this, "블루투스를 켜주세요", Toast.LENGTH_SHORT).show()
            return
        }
        
        updateStatus("ESP32 장치 검색 중...")
        btnScan.isEnabled = false
        bleService?.startScan()
        
        // 10초 후 스캔 중지
        btnScan.postDelayed({
            bleService?.stopScan()
            btnScan.isEnabled = true
            if (!isConnected) {
                updateStatus("ESP32 장치를 찾을 수 없습니다\n다시 시도하세요")
            }
        }, 10000)
    }
    
    private fun sendTokenToESP32() {
        if (accessToken == null) {
            Toast.makeText(this, "토큰이 없습니다", Toast.LENGTH_SHORT).show()
            return
        }
        
        if (!isConnected) {
            Toast.makeText(this, "ESP32에 연결되지 않았습니다", Toast.LENGTH_SHORT).show()
            return
        }
        
        updateStatus("ESP32로 토큰 전송 중...")
        val success = bleService?.sendToken(accessToken!!) ?: false
        if (!success) {
            updateStatus("토큰 전송 실패")
        }
    }
    
    private fun isBluetoothEnabled(): Boolean {
        return bluetoothAdapter?.isEnabled == true
    }
    
    private fun updateStatus(message: String) {
        tvStatus.text = message
    }
    
    private fun displayUserInfo() {
        val prefs = getSharedPreferences("hanjin_prefs", Context.MODE_PRIVATE)
        val userId = prefs.getString("user_id", null)
        val expiresAt = prefs.getString("expires_at", null)
        val expiryDate = prefs.getString("expiry_date", null)
        
        val infoText = StringBuilder()
        
        // 로그인 아이디 표시
        if (userId != null) {
            infoText.append("로그인: $userId\n")
        }
        
        // 토큰 유효시간 표시 (토큰 전송 성공 후에만)
        if (expiresAt != null) {
            try {
                val dateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())
                dateFormat.timeZone = TimeZone.getTimeZone("UTC")
                val expiresAtDate = dateFormat.parse(expiresAt)
                val now = Date()
                
                if (expiresAtDate != null) {
                    val remaining = expiresAtDate.time - now.time
                    
                    if (remaining < 0) {
                        infoText.append("토큰 만료됨\n")
                    } else {
                        val days = remaining / (1000 * 60 * 60 * 24)
                        val hours = (remaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)
                        val minutes = (remaining % (1000 * 60 * 60)) / (1000 * 60)
                        
                        if (days > 0) {
                            infoText.append("토큰 유효: ${days}일 ${hours}시간\n")
                        } else if (hours > 0) {
                            infoText.append("토큰 유효: ${hours}시간 ${minutes}분\n")
                        } else {
                            infoText.append("토큰 유효: ${minutes}분\n")
                        }
                    }
                }
            } catch (e: Exception) {
                Log.e("MainActivity", "토큰 만료시간 파싱 오류", e)
                // 파싱 실패 시 원본 문자열 표시
                infoText.append("토큰 만료: $expiresAt\n")
            }
        }
        
        // 사용자 만료날짜 표시
        if (expiryDate != null) {
            try {
                val dateFormat = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
                val expiryDateParsed = dateFormat.parse(expiryDate)
                val today = Calendar.getInstance()
                today.set(Calendar.HOUR_OF_DAY, 0)
                today.set(Calendar.MINUTE, 0)
                today.set(Calendar.SECOND, 0)
                today.set(Calendar.MILLISECOND, 0)
                
                if (expiryDateParsed != null) {
                    val expiryCal = Calendar.getInstance()
                    expiryCal.time = expiryDateParsed
                    expiryCal.set(Calendar.HOUR_OF_DAY, 0)
                    expiryCal.set(Calendar.MINUTE, 0)
                    expiryCal.set(Calendar.SECOND, 0)
                    expiryCal.set(Calendar.MILLISECOND, 0)
                    
                    val daysUntilExpiry = ((expiryCal.timeInMillis - today.timeInMillis) / (1000 * 60 * 60 * 24)).toInt()
                    
                    if (daysUntilExpiry < 0) {
                        infoText.append("사용 만료: 만료됨")
                    } else if (daysUntilExpiry == 0) {
                        infoText.append("사용 만료: 오늘")
                    } else {
                        infoText.append("사용 만료: $expiryDate (${daysUntilExpiry}일 남음)")
                    }
                } else {
                    infoText.append("사용 만료: $expiryDate")
                }
            } catch (e: Exception) {
                Log.e("MainActivity", "만료날짜 파싱 오류", e)
                // 파싱 실패 시 원본 문자열 표시
                infoText.append("사용 만료: $expiryDate")
            }
        }
        
        tvUserInfo.text = infoText.toString()
    }
    
    private fun logout() {
        // SharedPreferences에서 로그인 정보 삭제
        val prefs = getSharedPreferences("hanjin_prefs", Context.MODE_PRIVATE)
        prefs.edit()
            .remove("access_token")
            .remove("user_id")
            .remove("expires_at")
            .remove("expiry_date")
            .putBoolean("is_logged_in", false)
            .apply()
        
        // BLE 연결 종료
        bleService?.disconnect()
        bleService?.stopScan()
        
        // LoginActivity로 이동
        val loginIntent = Intent(this, LoginActivity::class.java)
        loginIntent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(loginIntent)
        finish()
        
        Toast.makeText(this, "로그아웃되었습니다", Toast.LENGTH_SHORT).show()
    }
    
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        
        if (requestCode == REQUEST_BLUETOOTH_PERMISSIONS) {
            if (grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
                Toast.makeText(this, "블루투스 권한이 허용되었습니다", Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(this, "블루투스 권한이 필요합니다", Toast.LENGTH_LONG).show()
            }
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        bleService?.disconnect()
        bleService?.stopScan()
    }
}

