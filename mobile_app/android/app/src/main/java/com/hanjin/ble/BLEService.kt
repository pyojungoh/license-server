package com.hanjin.ble

import android.annotation.SuppressLint
import android.bluetooth.*
import android.bluetooth.le.BluetoothLeScanner
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.os.Build
import android.os.ParcelUuid
import android.util.Log
import com.hanjin.Config
import java.util.*

class BLEService(private val context: Context) {
    
    private var bluetoothAdapter: BluetoothAdapter? = null
    private var bluetoothLeScanner: BluetoothLeScanner? = null
    private var bluetoothGatt: BluetoothGatt? = null
    private var targetDevice: BluetoothDevice? = null
    private var serviceUuid: BluetoothGattService? = null
    private var characteristic: BluetoothGattCharacteristic? = null
    private var heartbeatCharacteristic: BluetoothGattCharacteristic? = null
    private var heartbeatTimer: Timer? = null
    
    var onDeviceFound: ((BluetoothDevice) -> Unit)? = null
    var onConnected: (() -> Unit)? = null
    var onDisconnected: (() -> Unit)? = null
    var onTokenSent: ((Boolean) -> Unit)? = null
    
    private val scanCallback = object : ScanCallback() {
        @SuppressLint("MissingPermission")
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            val device = result.device
            val deviceName = device.name
            
            // 모든 스캔 결과 로그 (디버깅용)
            if (deviceName != null) {
                Log.d("BLEService", "스캔 결과: name=$deviceName, address=${device.address}, rssi=${result.rssi}")
            } else {
                Log.d("BLEService", "스캔 결과: name=null, address=${device.address}, rssi=${result.rssi}")
            }
            
            // ESP32 장치 이름으로 필터링
            if (deviceName == Config.ESP32_DEVICE_NAME) {
                Log.d("BLEService", "✓✓✓ ESP32 장치 발견: $deviceName (${device.address})")
                stopScan()
                targetDevice = device
                onDeviceFound?.invoke(device)
            }
        }
        
        override fun onBatchScanResults(results: MutableList<ScanResult>?) {
            super.onBatchScanResults(results)
            results?.forEach { result ->
                val device = result.device
                val deviceName = device.name
                
                if (deviceName != null) {
                    Log.d("BLEService", "배치 스캔 결과: name=$deviceName, address=${device.address}, rssi=${result.rssi}")
                }
                
                // ESP32 장치 이름으로 필터링 (부분 매칭 지원)
                if (deviceName != null && (
                    deviceName == Config.ESP32_DEVICE_NAME || 
                    deviceName.startsWith("한진택배")
                )) {
                    Log.d("BLEService", "✓✓✓ ESP32 장치 발견 (배치): $deviceName (${device.address})")
                    stopScan()
                    targetDevice = device
                    onDeviceFound?.invoke(device)
                }
            }
        }
        
        override fun onScanFailed(errorCode: Int) {
            super.onScanFailed(errorCode)
            Log.e("BLEService", "스캔 실패: errorCode=$errorCode")
        }
    }
    
    private val gattCallback = object : BluetoothGattCallback() {
        @SuppressLint("MissingPermission")
        override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
            when (newState) {
                BluetoothProfile.STATE_CONNECTED -> {
                    Log.d("BLEService", "GATT 연결됨")
                    gatt.discoverServices()
                }
                BluetoothProfile.STATE_DISCONNECTED -> {
                    Log.d("BLEService", "GATT 연결 끊김")
                    onDisconnected?.invoke()
                }
            }
        }
        
        @SuppressLint("MissingPermission")
        override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS) {
                Log.d("BLEService", "서비스 탐색 완료")
                
                val service = gatt.getService(UUID.fromString(Config.ESP32_SERVICE_UUID))
                if (service != null) {
                    serviceUuid = service
                    characteristic = service.getCharacteristic(
                        UUID.fromString(Config.ESP32_CHARACTERISTIC_UUID)
                    )
                    heartbeatCharacteristic = service.getCharacteristic(
                        UUID.fromString(Config.ESP32_HEARTBEAT_CHAR_UUID)
                    )
                    
                    if (characteristic != null && heartbeatCharacteristic != null) {
                        Log.d("BLEService", "Characteristic 찾음 (토큰 + Heartbeat)")
                        startHeartbeat()  // Heartbeat 시작
                        onConnected?.invoke()
                    } else {
                        Log.e("BLEService", "Characteristic을 찾을 수 없음")
                    }
                } else {
                    Log.e("BLEService", "Service를 찾을 수 없음")
                }
            }
        }
        
        @SuppressLint("MissingPermission")
        override fun onCharacteristicWrite(
            gatt: BluetoothGatt,
            characteristic: BluetoothGattCharacteristic,
            status: Int
        ) {
            if (status == BluetoothGatt.GATT_SUCCESS) {
                Log.d("BLEService", "토큰 전송 성공")
                onTokenSent?.invoke(true)
            } else {
                Log.e("BLEService", "토큰 전송 실패: $status")
                onTokenSent?.invoke(false)
            }
        }
    }
    
    @SuppressLint("MissingPermission")
    fun startScan() {
        val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        bluetoothAdapter = bluetoothManager.adapter
        bluetoothLeScanner = bluetoothAdapter?.bluetoothLeScanner
        
        if (bluetoothAdapter == null) {
            Log.e("BLEService", "블루투스 어댑터를 사용할 수 없음")
            return
        }
        
        // 1단계: 이미 페어링된 기기에서 ESP32 찾기 (BLE HID로 연결된 경우)
        Log.d("BLEService", "페어링된 기기 목록 확인 중...")
        val bondedDevices = bluetoothAdapter?.bondedDevices
        if (bondedDevices == null || bondedDevices.isEmpty()) {
            Log.d("BLEService", "페어링된 기기가 없습니다.")
        } else {
            Log.d("BLEService", "페어링된 기기 수: ${bondedDevices.size}")
            bondedDevices.forEach { device ->
                val deviceName = device.name
                Log.d("BLEService", "페어링된 기기: name=$deviceName, address=${device.address}, type=${device.type}")
                
                // 이름이 정확히 일치하거나, "한진택배"로 시작하는 경우 ESP32로 인식
                // (이름이 깨져서 저장된 경우를 대비)
                if (deviceName != null && (
                    deviceName == Config.ESP32_DEVICE_NAME || 
                    deviceName.startsWith("한진택배")
                )) {
                    Log.d("BLEService", "✓✓✓ ESP32 발견 (페어링된 기기): $deviceName (${device.address})")
                    stopScan() // 스캔 중지
                    targetDevice = device
                    onDeviceFound?.invoke(device)
                    return
                }
            }
        }
        
        // 2단계: 페어링된 기기에서 못 찾으면 BLE 스캔 시작
        if (bluetoothLeScanner == null) {
            Log.e("BLEService", "BLE 스캐너를 사용할 수 없음")
            return
        }
        
        // 필터 없이 모든 BLE 장치 스캔 (이름으로 필터링은 콜백에서 처리)
        // ESP32가 Custom Service를 어드버타이징하지 않을 수 있어서 필터를 제거
        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .build()
        
        bluetoothLeScanner?.startScan(null, settings, scanCallback) // 필터 없이 스캔
        Log.d("BLEService", "BLE 스캔 시작 (필터 없음 - 모든 장치 스캔)")
    }
    
    @SuppressLint("MissingPermission")
    fun stopScan() {
        bluetoothLeScanner?.stopScan(scanCallback)
        Log.d("BLEService", "BLE 스캔 중지")
    }
    
    @SuppressLint("MissingPermission")
    fun connect() {
        if (targetDevice == null) {
            Log.e("BLEService", "연결할 장치가 없음")
            return
        }
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            bluetoothGatt = targetDevice?.connectGatt(context, false, gattCallback, BluetoothDevice.TRANSPORT_LE)
        } else {
            bluetoothGatt = targetDevice?.connectGatt(context, false, gattCallback)
        }
        Log.d("BLEService", "ESP32 연결 시도")
    }
    
    @SuppressLint("MissingPermission")
    fun sendToken(token: String): Boolean {
        if (characteristic == null || bluetoothGatt == null) {
            Log.e("BLEService", "Characteristic 또는 GATT가 null")
            return false
        }
        
        characteristic?.value = token.toByteArray(Charsets.UTF_8)
        characteristic?.writeType = BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
        
        val result = bluetoothGatt?.writeCharacteristic(characteristic)
        Log.d("BLEService", "토큰 전송 시도: $result")
        return result == true
    }
    
    @SuppressLint("MissingPermission")
    fun disconnect() {
        stopHeartbeat()  // Heartbeat 중지
        bluetoothGatt?.disconnect()
        bluetoothGatt?.close()
        bluetoothGatt = null
        serviceUuid = null
        characteristic = null
        heartbeatCharacteristic = null
        Log.d("BLEService", "ESP32 연결 종료")
    }
    
    // Heartbeat 전송 시작 (30초마다)
    private fun startHeartbeat() {
        stopHeartbeat()  // 기존 타이머 중지
        
        heartbeatTimer = Timer()
        heartbeatTimer?.scheduleAtFixedRate(object : TimerTask() {
            override fun run() {
                sendHeartbeat()
            }
        }, 0, 30000)  // 30초마다 실행
        
        Log.d("BLEService", "Heartbeat 시작 (30초 간격)")
    }
    
    // Heartbeat 전송 중지
    private fun stopHeartbeat() {
        heartbeatTimer?.cancel()
        heartbeatTimer = null
        Log.d("BLEService", "Heartbeat 중지")
    }
    
    // Heartbeat 전송
    @SuppressLint("MissingPermission")
    private fun sendHeartbeat() {
        if (heartbeatCharacteristic != null && bluetoothGatt != null) {
            heartbeatCharacteristic?.value = "HEARTBEAT".toByteArray(Charsets.UTF_8)
            bluetoothGatt?.writeCharacteristic(heartbeatCharacteristic)
            // Log.d("BLEService", "Heartbeat 전송")
        }
    }
}

