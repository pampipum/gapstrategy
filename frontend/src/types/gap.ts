export interface Gap {
    symbol: string;
    companyName: string;
    sector: string;
    date: string;
    gap_type: 'up' | 'down';
    gap_size: number;
    prev_high: number;
    prev_low: number;
    current_open: number;
    price: number;
    first_candle_high: number;
    first_candle_low: number;
    entry_price: number;
    stop_loss: number;
    target: number;
    risk_amount: number;
    reward_amount: number;
    volume: number;
    avg_volume: number;
    market_cap: number;
    relative_volume: number;
}

export interface ScanLogEntry {
    symbol: string;
    companyName: string;
    sector: string;
    status: string;
    time: string;
    has_gap: boolean;
}

export interface ChartDataPoint {
    date: string;
    count: number;
    up: number;
    down: number;
}