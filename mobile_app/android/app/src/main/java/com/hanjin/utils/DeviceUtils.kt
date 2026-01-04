package com.hanjin.utils

import android.content.Context
import android.content.SharedPreferences
import java.util.UUID

/**
 * 기기 UUID 관리 유틸리티
 * 1인 1기기 정책을 위한 고유 식별자 생성 및 저장
 */
object DeviceUtils {
    private const val PREFS_NAME = "hanjin_device_prefs"
    private const val KEY_DEVICE_UUID = "device_uuid"
    
    /**
     * 기기 UUID 가져오기 (없으면 생성)
     * 앱 설치 후 처음 실행 시 생성되며, 이후 계속 유지됩니다.
     */
    fun getDeviceUUID(context: Context): String {
        val prefs: SharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        var deviceUuid = prefs.getString(KEY_DEVICE_UUID, null)
        
        if (deviceUuid == null) {
            // UUID 생성 (예: 550e8400-e29b-41d4-a716-446655440000)
            deviceUuid = UUID.randomUUID().toString()
            prefs.edit().putString(KEY_DEVICE_UUID, deviceUuid).apply()
        }
        
        return deviceUuid
    }
    
    /**
     * 기기 UUID 재설정 (기기 변경 시 사용)
     */
    fun resetDeviceUUID(context: Context) {
        val prefs: SharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().remove(KEY_DEVICE_UUID).apply()
    }
}





