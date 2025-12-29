package com.hanjin.api

import android.util.Log
import com.hanjin.Config
import com.hanjin.models.LoginRequest
import com.hanjin.models.LoginResponse
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.POST

/**
 * 서버 API 인터페이스
 */
interface ApiService {
    @POST(Config.API_LOGIN)
    suspend fun login(@Body request: LoginRequest): LoginResponse
}

/**
 * Retrofit API 클라이언트 생성
 */
object ApiClient {
    private val loggingInterceptor = HttpLoggingInterceptor { message ->
        Log.d("ApiClient", message)
    }.apply {
        level = HttpLoggingInterceptor.Level.BODY  // 요청/응답 본문 전체 로깅
    }
    
    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .build()
    
    private val retrofit = Retrofit.Builder()
        .baseUrl(Config.SERVER_URL)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
    
    val apiService: ApiService = retrofit.create(ApiService::class.java)
}

