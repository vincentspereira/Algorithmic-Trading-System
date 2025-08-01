/**
 * Java Client Library for Algorithmic Trading System API
 * 
 * This comprehensive Java client provides easy access to all API endpoints
 * with proper error handling, authentication, and type safety.
 */

package com.tradingsystem.api;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import okhttp3.*;
import okhttp3.logging.HttpLoggingInterceptor;

import java.io.IOException;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

/**
 * Main client class for interacting with the Trading System API
 */
public class TradingSystemClient {
    private static final String DEFAULT_BASE_URL = "https://api.trading-system.com";
    private static final String SANDBOX_BASE_URL = "https://sandbox-api.trading-system.com";
    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");
    
    private final OkHttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final String baseUrl;
    private String accessToken;
    private String refreshToken;
    
    /**
     * Constructor for TradingSystemClient
     * 
     * @param sandbox Whether to use sandbox environment
     */
    public TradingSystemClient(boolean sandbox) {
        this.baseUrl = sandbox ? SANDBOX_BASE_URL : DEFAULT_BASE_URL;
        
        // Configure HTTP client
        HttpLoggingInterceptor logging = new HttpLoggingInterceptor();
        logging.setLevel(HttpLoggingInterceptor.Level.BASIC);
        
        this.httpClient = new OkHttpClient.Builder()
            .addInterceptor(logging)
            .addInterceptor(this::addAuthHeader)
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build();
        
        // Configure JSON mapper
        this.objectMapper = new ObjectMapper();
        objectMapper.registerModule(new JavaTimeModule());
        objectMapper.setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);
    }
    
    /**
     * Interceptor to add authentication header
     */
    private Response addAuthHeader(Interceptor.Chain chain) throws IOException {
        Request original = chain.request();
        
        if (accessToken != null && !original.url().encodedPath().contains("/auth/")) {
            Request authenticated = original.newBuilder()
                .header("Authorization", "Bearer " + accessToken)
                .build();
            return chain.proceed(authenticated);
        }
        
        return chain.proceed(original);
    }
    
    /**
     * Authentication Methods
     */
    
    public CompletableFuture<LoginResponse> login(String username, String password) {
        return login(username, password, false);
    }
    
    public CompletableFuture<LoginResponse> login(String username, String password, boolean rememberMe) {
        LoginRequest request = new LoginRequest(username, password, rememberMe);
        
        return makeRequest("POST", "/auth/login", request, LoginResponse.class)
            .thenApply(response -> {
                this.accessToken = response.getAccessToken();
                this.refreshToken = response.getRefreshToken();
                return response;
            });
    }
    
    public CompletableFuture<LoginResponse> refreshAccessToken() {
        if (refreshToken == null) {
            return CompletableFuture.failedFuture(
                new IllegalStateException("No refresh token available"));
        }
        
        RefreshRequest request = new RefreshRequest(refreshToken);
        
        return makeRequest("POST", "/auth/refresh", request, LoginResponse.class)
            .thenApply(response -> {
                this.accessToken = response.getAccessToken();
                if (response.getRefreshToken() != null) {
                    this.refreshToken = response.getRefreshToken();
                }
                return response;
            });
    }
    
    /**
     * Strategy Management Methods
     */
    
    public CompletableFuture<StrategiesResponse> getStrategies() {
        return getStrategies(new StrategyListOptions());
    }
    
    public CompletableFuture<StrategiesResponse> getStrategies(StrategyListOptions options) {
        HttpUrl.Builder urlBuilder = HttpUrl.parse(baseUrl + "/strategies").newBuilder();
        
        if (options.getPage() != null) {
            urlBuilder.addQueryParameter("page", options.getPage().toString());
        }
        if (options.getLimit() != null) {
            urlBuilder.addQueryParameter("limit", options.getLimit().toString());
        }
        if (options.getStatus() != null) {
            urlBuilder.addQueryParameter("status", options.getStatus().toString().toLowerCase());
        }
        if (options.getAssetClass() != null) {
            urlBuilder.addQueryParameter("asset_class", options.getAssetClass().toString().toLowerCase());
        }
        
        return makeRequest("GET", urlBuilder.build().encodedPath() + "?" + urlBuilder.build().encodedQuery(), 
                          null, StrategiesResponse.class);
    }
    
    public CompletableFuture<Strategy> createStrategy(CreateStrategyRequest request) {
        return makeRequest("POST", "/strategies", request, Strategy.class);
    }
    
    public CompletableFuture<Strategy> getStrategy(String strategyId) {
        return makeRequest("GET", "/strategies/" + strategyId, null, Strategy.class);
    }
    
    public CompletableFuture<Strategy> updateStrategy(String strategyId, UpdateStrategyRequest request) {
        return makeRequest("PUT", "/strategies/" + strategyId, request, Strategy.class);
    }
    
    public CompletableFuture<Void> deleteStrategy(String strategyId) {
        return makeRequest("DELETE", "/strategies/" + strategyId, null, Void.class);
    }
    
    /**
     * Market Data Methods
     */
    
    public CompletableFuture<Quote> getQuote(String symbol) {
        return getQuote(symbol, null);
    }
    
    public CompletableFuture<Quote> getQuote(String symbol, List<String> fields) {
        HttpUrl.Builder urlBuilder = HttpUrl.parse(baseUrl + "/market-data/quotes/" + symbol).newBuilder();
        
        if (fields != null && !fields.isEmpty()) {
            urlBuilder.addQueryParameter("fields", String.join(",", fields));
        }
        
        return makeRequest("GET", urlBuilder.build().encodedPath() + 
                          (urlBuilder.build().encodedQuery() != null ? "?" + urlBuilder.build().encodedQuery() : ""), 
                          null, Quote.class);
    }
    
    public CompletableFuture<HistoricalDataResponse> getHistoricalData(String symbol, LocalDate startDate, 
                                                                      LocalDate endDate) {
        return getHistoricalData(symbol, startDate, endDate, "1d");
    }
    
    public CompletableFuture<HistoricalDataResponse> getHistoricalData(String symbol, LocalDate startDate, 
                                                                      LocalDate endDate, String interval) {
        HttpUrl.Builder urlBuilder = HttpUrl.parse(baseUrl + "/market-data/historical/" + symbol).newBuilder()
            .addQueryParameter("start_date", startDate.toString())
            .addQueryParameter("end_date", endDate.toString())
            .addQueryParameter("interval", interval);
        
        return makeRequest("GET", urlBuilder.build().encodedPath() + "?" + urlBuilder.build().encodedQuery(), 
                          null, HistoricalDataResponse.class);
    }
    
    /**
     * Backtesting Methods
     */
    
    public CompletableFuture<BacktestResponse> runBacktest(BacktestRequest request) {
        return makeRequest("POST", "/backtesting/run", request, BacktestResponse.class);
    }
    
    public CompletableFuture<BacktestResults> getBacktestResults(String backtestId) {
        return makeRequest("GET", "/backtesting/" + backtestId, null, BacktestResults.class);
    }
    
    /**
     * Trading Methods
     */
    
    public CompletableFuture<OrdersResponse> getOrders() {
        return getOrders(new OrderListOptions());
    }
    
    public CompletableFuture<OrdersResponse> getOrders(OrderListOptions options) {
        HttpUrl.Builder urlBuilder = HttpUrl.parse(baseUrl + "/orders").newBuilder();
        
        if (options.getStatus() != null) {
            urlBuilder.addQueryParameter("status", options.getStatus().toString().toLowerCase());
        }
        if (options.getSymbol() != null) {
            urlBuilder.addQueryParameter("symbol", options.getSymbol());
        }
        
        return makeRequest("GET", urlBuilder.build().encodedPath() + 
                          (urlBuilder.build().encodedQuery() != null ? "?" + urlBuilder.build().encodedQuery() : ""), 
                          null, OrdersResponse.class);
    }
    
    public CompletableFuture<Order> placeOrder(OrderRequest request) {
        return makeRequest("POST", "/orders", request, Order.class);
    }
    
    /**
     * Generic HTTP request method
     */
    private <T> CompletableFuture<T> makeRequest(String method, String path, Object requestBody, Class<T> responseType) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                Request.Builder requestBuilder = new Request.Builder()
                    .url(baseUrl + path)
                    .header("User-Agent", "TradingSystem-Java-Client/1.0");
                
                if (requestBody != null) {
                    String json = objectMapper.writeValueAsString(requestBody);
                    RequestBody body = RequestBody.create(json, JSON);
                    
                    switch (method.toUpperCase()) {
                        case "POST":
                            requestBuilder.post(body);
                            break;
                        case "PUT":
                            requestBuilder.put(body);
                            break;
                        case "PATCH":
                            requestBuilder.patch(body);
                            break;
                        default:
                            throw new IllegalArgumentException("Unsupported method with body: " + method);
                    }
                } else {
                    switch (method.toUpperCase()) {
                        case "GET":
                            requestBuilder.get();
                            break;
                        case "DELETE":
                            requestBuilder.delete();
                            break;
                        case "POST":
                            requestBuilder.post(RequestBody.create("", JSON));
                            break;
                        default:
                            throw new IllegalArgumentException("Unsupported method: " + method);
                    }
                }
                
                try (Response response = httpClient.newCall(requestBuilder.build()).execute()) {
                    if (!response.isSuccessful()) {
                        String errorBody = response.body() != null ? response.body().string() : "";
                        throw new ApiException(response.code(), response.message(), errorBody);
                    }
                    
                    if (responseType == Void.class) {
                        return null;
                    }
                    
                    String responseBody = response.body().string();
                    return objectMapper.readValue(responseBody, responseType);
                }
                
            } catch (IOException e) {
                throw new RuntimeException("Request failed", e);
            }
        });
    }
    
    /**
     * Close the HTTP client
     */
    public void close() {
        httpClient.dispatcher().executorService().shutdown();
        httpClient.connectionPool().evictAll();
    }
}

/**
 * Data Transfer Objects (DTOs)
 */

// Authentication DTOs
class LoginRequest {
    private String username;
    private String password;
    private boolean rememberMe;
    
    public LoginRequest(String username, String password, boolean rememberMe) {
        this.username = username;
        this.password = password;
        this.rememberMe = rememberMe;
    }
    
    // Getters and setters
    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }
    public String getPassword() { return password; }
    public void setPassword(String password) { this.password = password; }
    public boolean isRememberMe() { return rememberMe; }
    public void setRememberMe(boolean rememberMe) { this.rememberMe = rememberMe; }
}

class RefreshRequest {
    private String refreshToken;
    
    public RefreshRequest(String refreshToken) {
        this.refreshToken = refreshToken;
    }
    
    public String getRefreshToken() { return refreshToken; }
    public void setRefreshToken(String refreshToken) { this.refreshToken = refreshToken; }
}

class LoginResponse {
    private String accessToken;
    private String tokenType;
    private int expiresIn;
    private String refreshToken;
    
    // Getters and setters
    public String getAccessToken() { return accessToken; }
    public void setAccessToken(String accessToken) { this.accessToken = accessToken; }
    public String getTokenType() { return tokenType; }
    public void setTokenType(String tokenType) { this.tokenType = tokenType; }
    public int getExpiresIn() { return expiresIn; }
    public void setExpiresIn(int expiresIn) { this.expiresIn = expiresIn; }
    public String getRefreshToken() { return refreshToken; }
    public void setRefreshToken(String refreshToken) { this.refreshToken = refreshToken; }
}

// Strategy DTOs
enum StrategyStatus { ACTIVE, INACTIVE, DRAFT }
enum AssetClass { STOCKS, FOREX, CRYPTO, COMMODITIES, BONDS }

class StrategyListOptions {
    private Integer page;
    private Integer limit;
    private StrategyStatus status;
    private AssetClass assetClass;
    
    // Getters and setters
    public Integer getPage() { return page; }
    public void setPage(Integer page) { this.page = page; }
    public Integer getLimit() { return limit; }
    public void setLimit(Integer limit) { this.limit = limit; }
    public StrategyStatus getStatus() { return status; }
    public void setStatus(StrategyStatus status) { this.status = status; }
    public AssetClass getAssetClass() { return assetClass; }
    public void setAssetClass(AssetClass assetClass) { this.assetClass = assetClass; }
}

class Strategy {
    private String id;
    private String name;
    private String description;
    private StrategyStatus status;
    private AssetClass assetClass;
    private String strategyType;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private Map<String, Object> parameters;
    private PerformanceMetrics performance;
    
    // Getters and setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public StrategyStatus getStatus() { return status; }
    public void setStatus(StrategyStatus status) { this.status = status; }
    public AssetClass getAssetClass() { return assetClass; }
    public void setAssetClass(AssetClass assetClass) { this.assetClass = assetClass; }
    public String getStrategyType() { return strategyType; }
    public void setStrategyType(String strategyType) { this.strategyType = strategyType; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
    public Map<String, Object> getParameters() { return parameters; }
    public void setParameters(Map<String, Object> parameters) { this.parameters = parameters; }
    public PerformanceMetrics getPerformance() { return performance; }
    public void setPerformance(PerformanceMetrics performance) { this.performance = performance; }
}

class CreateStrategyRequest {
    private String name;
    private String description;
    private AssetClass assetClass;
    private String strategyType;
    private Map<String, Object> parameters;
    private Map<String, Object> riskManagement;
    
    // Constructors
    public CreateStrategyRequest() {}
    
    public CreateStrategyRequest(String name, String description, AssetClass assetClass, String strategyType) {
        this.name = name;
        this.description = description;
        this.assetClass = assetClass;
        this.strategyType = strategyType;
    }
    
    // Getters and setters
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public AssetClass getAssetClass() { return assetClass; }
    public void setAssetClass(AssetClass assetClass) { this.assetClass = assetClass; }
    public String getStrategyType() { return strategyType; }
    public void setStrategyType(String strategyType) { this.strategyType = strategyType; }
    public Map<String, Object> getParameters() { return parameters; }
    public void setParameters(Map<String, Object> parameters) { this.parameters = parameters; }
    public Map<String, Object> getRiskManagement() { return riskManagement; }
    public void setRiskManagement(Map<String, Object> riskManagement) { this.riskManagement = riskManagement; }
}

class UpdateStrategyRequest {
    private String name;
    private String description;
    private StrategyStatus status;
    private Map<String, Object> parameters;
    
    // Getters and setters
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public StrategyStatus getStatus() { return status; }
    public void setStatus(StrategyStatus status) { this.status = status; }
    public Map<String, Object> getParameters() { return parameters; }
    public void setParameters(Map<String, Object> parameters) { this.parameters = parameters; }
}

class StrategiesResponse {
    private List<Strategy> strategies;
    private Pagination pagination;
    
    // Getters and setters
    public List<Strategy> getStrategies() { return strategies; }
    public void setStrategies(List<Strategy> strategies) { this.strategies = strategies; }
    public Pagination getPagination() { return pagination; }
    public void setPagination(Pagination pagination) { this.pagination = pagination; }
}

class PerformanceMetrics {
    private double totalReturn;
    private double sharpeRatio;
    private double maxDrawdown;
    private double winRate;
    
    // Getters and setters
    public double getTotalReturn() { return totalReturn; }
    public void setTotalReturn(double totalReturn) { this.totalReturn = totalReturn; }
    public double getSharpeRatio() { return sharpeRatio; }
    public void setSharpeRatio(double sharpeRatio) { this.sharpeRatio = sharpeRatio; }
    public double getMaxDrawdown() { return maxDrawdown; }
    public void setMaxDrawdown(double maxDrawdown) { this.maxDrawdown = maxDrawdown; }
    public double getWinRate() { return winRate; }
    public void setWinRate(double winRate) { this.winRate = winRate; }
}

// Market Data DTOs
class Quote {
    private String symbol;
    private double bid;
    private double ask;
    private double last;
    private long volume;
    private LocalDateTime timestamp;
    private double change;
    private double changePercent;
    
    // Getters and setters
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    public double getBid() { return bid; }
    public void setBid(double bid) { this.bid = bid; }
    public double getAsk() { return ask; }
    public void setAsk(double ask) { this.ask = ask; }
    public double getLast() { return last; }
    public void setLast(double last) { this.last = last; }
    public long getVolume() { return volume; }
    public void setVolume(long volume) { this.volume = volume; }
    public LocalDateTime getTimestamp() { return timestamp; }
    public void setTimestamp(LocalDateTime timestamp) { this.timestamp = timestamp; }
    public double getChange() { return change; }
    public void setChange(double change) { this.change = change; }
    public double getChangePercent() { return changePercent; }
    public void setChangePercent(double changePercent) { this.changePercent = changePercent; }
}

class HistoricalDataResponse {
    private String symbol;
    private List<OHLCV> data;
    
    // Getters and setters
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    public List<OHLCV> getData() { return data; }
    public void setData(List<OHLCV> data) { this.data = data; }
}

class OHLCV {
    private LocalDateTime timestamp;
    private double open;
    private double high;
    private double low;
    private double close;
    private long volume;
    
    // Getters and setters
    public LocalDateTime getTimestamp() { return timestamp; }
    public void setTimestamp(LocalDateTime timestamp) { this.timestamp = timestamp; }
    public double getOpen() { return open; }
    public void setOpen(double open) { this.open = open; }
    public double getHigh() { return high; }
    public void setHigh(double high) { this.high = high; }
    public double getLow() { return low; }
    public void setLow(double low) { this.low = low; }
    public double getClose() { return close; }
    public void setClose(double close) { this.close = close; }
    public long getVolume() { return volume; }
    public void setVolume(long volume) { this.volume = volume; }
}

// Backtesting DTOs
class BacktestRequest {
    private String strategyId;
    private LocalDate startDate;
    private LocalDate endDate;
    private double initialCapital;
    private String benchmark;
    private Map<String, Object> parameters;
    
    // Constructors
    public BacktestRequest() {}
    
    public BacktestRequest(String strategyId, LocalDate startDate, LocalDate endDate, double initialCapital) {
        this.strategyId = strategyId;
        this.startDate = startDate;
        this.endDate = endDate;
        this.initialCapital = initialCapital;
    }
    
    // Getters and setters
    public String getStrategyId() { return strategyId; }
    public void setStrategyId(String strategyId) { this.strategyId = strategyId; }
    public LocalDate getStartDate() { return startDate; }
    public void setStartDate(LocalDate startDate) { this.startDate = startDate; }
    public LocalDate getEndDate() { return endDate; }
    public void setEndDate(LocalDate endDate) { this.endDate = endDate; }
    public double getInitialCapital() { return initialCapital; }
    public void setInitialCapital(double initialCapital) { this.initialCapital = initialCapital; }
    public String getBenchmark() { return benchmark; }
    public void setBenchmark(String benchmark) { this.benchmark = benchmark; }
    public Map<String, Object> getParameters() { return parameters; }
    public void setParameters(Map<String, Object> parameters) { this.parameters = parameters; }
}

enum BacktestStatus { RUNNING, COMPLETED, FAILED }

class BacktestResponse {
    private String backtestId;
    private BacktestStatus status;
    private LocalDateTime estimatedCompletion;
    
    // Getters and setters
    public String getBacktestId() { return backtestId; }
    public void setBacktestId(String backtestId) { this.backtestId = backtestId; }
    public BacktestStatus getStatus() { return status; }
    public void setStatus(BacktestStatus status) { this.status = status; }
    public LocalDateTime getEstimatedCompletion() { return estimatedCompletion; }
    public void setEstimatedCompletion(LocalDateTime estimatedCompletion) { this.estimatedCompletion = estimatedCompletion; }
}

class BacktestResults {
    private String backtestId;
    private BacktestStatus status;
    private PerformanceMetrics performance;
    private List<Trade> trades;
    private List<EquityPoint> equityCurve;
    
    // Getters and setters
    public String getBacktestId() { return backtestId; }
    public void setBacktestId(String backtestId) { this.backtestId = backtestId; }
    public BacktestStatus getStatus() { return status; }
    public void setStatus(BacktestStatus status) { this.status = status; }
    public PerformanceMetrics getPerformance() { return performance; }
    public void setPerformance(PerformanceMetrics performance) { this.performance = performance; }
    public List<Trade> getTrades() { return trades; }
    public void setTrades(List<Trade> trades) { this.trades = trades; }
    public List<EquityPoint> getEquityCurve() { return equityCurve; }
    public void setEquityCurve(List<EquityPoint> equityCurve) { this.equityCurve = equityCurve; }
}

// Trading DTOs
enum OrderSide { BUY, SELL }
enum OrderType { MARKET, LIMIT, STOP, STOP_LIMIT }
enum OrderStatus { PENDING, FILLED, CANCELLED, REJECTED }
enum TimeInForce { DAY, GTC, IOC, FOK }

class OrderListOptions {
    private OrderStatus status;
    private String symbol;
    
    // Getters and setters
    public OrderStatus getStatus() { return status; }
    public void setStatus(OrderStatus status) { this.status = status; }
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
}

class OrderRequest {
    private String symbol;
    private OrderSide side;
    private OrderType orderType;
    private int quantity;
    private Double price;
    private Double stopPrice;
    private TimeInForce timeInForce;
    
    // Constructors
    public OrderRequest() {}
    
    public OrderRequest(String symbol, OrderSide side, OrderType orderType, int quantity) {
        this.symbol = symbol;
        this.side = side;
        this.orderType = orderType;
        this.quantity = quantity;
        this.timeInForce = TimeInForce.DAY;
    }
    
    // Getters and setters
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    public OrderSide getSide() { return side; }
    public void setSide(OrderSide side) { this.side = side; }
    public OrderType getOrderType() { return orderType; }
    public void setOrderType(OrderType orderType) { this.orderType = orderType; }
    public int getQuantity() { return quantity; }
    public void setQuantity(int quantity) { this.quantity = quantity; }
    public Double getPrice() { return price; }
    public void setPrice(Double price) { this.price = price; }
    public Double getStopPrice() { return stopPrice; }
    public void setStopPrice(Double stopPrice) { this.stopPrice = stopPrice; }
    public TimeInForce getTimeInForce() { return timeInForce; }
    public void setTimeInForce(TimeInForce timeInForce) { this.timeInForce = timeInForce; }
}

class Order {
    private String id;
    private String symbol;
    private OrderSide side;
    private OrderType orderType;
    private int quantity;
    private int filledQuantity;
    private Double price;
    private Double averageFillPrice;
    private OrderStatus status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    
    // Getters and setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    public OrderSide getSide() { return side; }
    public void setSide(OrderSide side) { this.side = side; }
    public OrderType getOrderType() { return orderType; }
    public void setOrderType(OrderType orderType) { this.orderType = orderType; }
    public int getQuantity() { return quantity; }
    public void setQuantity(int quantity) { this.quantity = quantity; }
    public int getFilledQuantity() { return filledQuantity; }
    public void setFilledQuantity(int filledQuantity) { this.filledQuantity = filledQuantity; }
    public Double getPrice() { return price; }
    public void setPrice(Double price) { this.price = price; }
    public Double getAverageFillPrice() { return averageFillPrice; }
    public void setAverageFillPrice(Double averageFillPrice) { this.averageFillPrice = averageFillPrice; }
    public OrderStatus getStatus() { return status; }
    public void setStatus(OrderStatus status) { this.status = status; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}

class OrdersResponse {
    private List<Order> orders;
    private Pagination pagination;
    
    // Getters and setters
    public List<Order> getOrders() { return orders; }
    public void setOrders(List<Order> orders) { this.orders = orders; }
    public Pagination getPagination() { return pagination; }
    public void setPagination(Pagination pagination) { this.pagination = pagination; }
}

class Trade {
    private String id;
    private String symbol;
    private OrderSide side;
    private int quantity;
    private double price;
    private LocalDateTime timestamp;
    private double pnl;
    
    // Getters and setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    public OrderSide getSide() { return side; }
    public void setSide(OrderSide side) { this.side = side; }
    public int getQuantity() { return quantity; }
    public void setQuantity(int quantity) { this.quantity = quantity; }
    public double getPrice() { return price; }
    public void setPrice(double price) { this.price = price; }
    public LocalDateTime getTimestamp() { return timestamp; }
    public void setTimestamp(LocalDateTime timestamp) { this.timestamp = timestamp; }
    public double getPnl() { return pnl; }
    public void setPnl(double pnl) { this.pnl = pnl; }
}

// Common DTOs
class Pagination {
    private int page;
    private int limit;
    private int total;
    private int pages;
    
    // Getters and setters
    public int getPage() { return page; }
    public void setPage(int page) { this.page = page; }
    public int getLimit() { return limit; }
    public void setLimit(int limit) { this.limit = limit; }
    public int getTotal() { return total; }
    public void setTotal(int total) { this.total = total; }
    public int getPages() { return pages; }
    public void setPages(int pages) { this.pages = pages; }
}

class EquityPoint {
    private LocalDate date;
    private double value;
    
    // Getters and setters
    public LocalDate getDate() { return date; }
    public void setDate(LocalDate date) { this.date = date; }
    public double getValue() { return value; }
    public void setValue(double value) { this.value = value; }
}

/**
 * Custom exception for API errors
 */
class ApiException extends RuntimeException {
    private final int statusCode;
    private final String responseBody;
    
    public ApiException(int statusCode, String message, String responseBody) {
        super(message);
        this.statusCode = statusCode;
        this.responseBody = responseBody;
    }
    
    public int getStatusCode() { return statusCode; }
    public String getResponseBody() { return responseBody; }
}