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
    
    var onDeviceFound: ((BluetoothDevice) -> Unit)? = null
    var onConnected: (() -> Unit)? = null
    var onDisconnected: (() -> Unit)? = null
    var onTokenSent: ((Boolean) -> Unit)? = null
    
    private val scanCallback = object : ScanCallback() {
        @SuppressLint("MissingPermission")
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            val device = result.device
            val deviceName = device.name
            
            Log.d("BLEService", "스캔 결과: $deviceName, Address: ${device.address}")
            
            // ESP32 장치 이름으로 필터링
            if (deviceName == Config.ESP32_DEVICE_NAME) {
                Log.d("BLEService", "ESP32 장치 발견: $deviceName")
                stopScan()
                targetDevice = device
                onDeviceFound?.invoke(device)
            }
        }
        
        override fun onScanFailed(errorCode: Int) {
            Log.e("BLEService", "스캔 실패: $errorCode")
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
                    
                    if (characteristic != null) {
                        Log.d("BLEService", "Characteristic 찾음")
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
        
        if (bluetoothLeScanner == null) {
            Log.e("BLEService", "BLE 스캐너를 사용할 수 없음")
            return
        }
        
        val filter = ScanFilter.Builder()
            .setServiceUuid(ParcelUuid(UUID.fromString(Config.ESP32_SERVICE_UUID)))
            .build()
        
        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .build()
        
        bluetoothLeScanner?.startScan(listOf(filter), settings, scanCallback)
        Log.d("BLEService", "BLE 스캔 시작")
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
        bluetoothGatt?.disconnect()
        bluetoothGatt?.close()
        bluetoothGatt = null
        serviceUuid = null
        characteristic = null
        Log.d("BLEService", "ESP32 연결 종료")
    }
}

