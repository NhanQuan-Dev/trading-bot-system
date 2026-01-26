import React, { useState, useMemo } from 'react';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Download, Eye, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";

interface Trade {
    trade_id: string;
    symbol: string;
    side: string;
    entry_time: string;
    entry_price: number;  // Average entry price (after scale-in)
    exit_time: string;
    exit_price: number;
    quantity: number;  // Total quantity (after scale-in)
    pnl: number;
    pnl_percent: number;
    status: string;
    mae?: number;
    mfe?: number;
    maker_fee?: number;
    taker_fee?: number;
    funding_fee?: number;
    entry_reason?: Record<string, any>;
    exit_reason?: Record<string, any>;
    // Initial entry (before scale-in)
    initial_entry_price?: number;
    initial_entry_quantity?: number;
    // Receipt fields
    gross_pnl?: number;
    net_pnl?: number;
    slippage?: number;
    entry_commission?: number;
    exit_commission?: number;
}

interface BacktestEvent {
    id: string;
    timestamp: string;
    event_type: string;
    details: Record<string, any>;
    trade_id?: string;
}

interface BacktestEvent {
    id: string;
    timestamp: string;
    event_type: string;
    details: Record<string, any>;
    trade_id?: string;
}

const PnLReceipt = ({ trade, backtestId }: { trade: Trade, backtestId: string }) => {
    const [events, setEvents] = useState<BacktestEvent[]>([]);
    const [loadingEvents, setLoadingEvents] = useState(false);

    React.useEffect(() => {
        const fetchEvents = async () => {
            if (!trade.trade_id || !backtestId) return;
            setLoadingEvents(true);
            try {
                const token = localStorage.getItem('access_token');
                const headers: HeadersInit = token ? { 'Authorization': `Bearer ${token}` } : {};
                const response = await fetch(`/api/v1/backtests/${backtestId}/events?trade_id=${trade.trade_id}`, { headers });
                if (response.ok) {
                    const data = await response.json();
                    setEvents(data);
                }
            } catch (error) {
                console.error("Failed to fetch backtest events:", error);
            } finally {
                setLoadingEvents(false);
            }
        };
        fetchEvents();
    }, [trade.trade_id, backtestId]);

    const entryValue = trade.entry_price * trade.quantity;
    const exitValue = trade.exit_price * trade.quantity;
    const isLong = trade.side?.toLowerCase() === 'long' || trade.side?.toLowerCase() === 'buy';

    // Simulated/Mock data for the "Explanation" parts as requested
    const context = trade.exit_reason?.calculation_context || {
        leverage: 20,
        fee_setup: { maker_rate: "0.02%", taker_rate: "0.05%" },
        slippage_tolerance: "0.1%"
    };

    return (
        <div className="p-6 bg-muted/30 rounded-lg border border-border/50 my-2 mx-4 animate-in fade-in slide-in-from-top-2 duration-300">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Section 1: Action Timeline */}
                <div className="space-y-4">
                    <h4 className="text-sm font-semibold text-primary uppercase tracking-wider flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-primary" />
                        Action Timeline
                    </h4>
                    <div className="relative border-l-2 border-border ml-2 pl-6 space-y-6">
                        {events.length > 0 ? (
                            events.map((event, idx) => {
                                const type = event.event_type.toUpperCase();
                                const isEntry = type === 'TRADE_OPENED';
                                const isExit = type === 'TRADE_CLOSED' || type === 'SL_HIT' || type === 'TP_HIT' || type === 'TRAILING_STOP_HIT' || type === 'LIQUIDATION';
                                const isLevelUpdate = type === 'LEVELS_UPDATED';
                                const isPartial = type === 'PARTIAL_CLOSE';
                                const isScaleIn = type === 'SCALE_IN';

                                return (
                                    <div key={event.id} className="relative">
                                        <div className={cn(
                                            "absolute -left-[33px] top-1 w-4 h-4 rounded-full bg-background border-2",
                                            isEntry ? "border-primary" :
                                                isExit ? "border-red-500" :
                                                    isPartial ? "border-orange-500" :
                                                        isScaleIn ? "border-blue-500" :
                                                            "border-muted-foreground/50"
                                        )} />
                                        <p className="text-xs font-medium text-white">
                                            Action {idx + 1}: {event.event_type.replace(/_/g, ' ')}
                                            {event.details.reason && ` (${event.details.reason})`}
                                        </p>
                                        <div className="mt-1 p-2 bg-background/50 rounded text-[11px] font-mono text-muted-foreground border border-border/30 whitespace-pre-wrap break-all">
                                            {isEntry && `Price: $${event.details.price?.toLocaleString()} | Qty: ${event.details.quantity}`}
                                            {isExit && `Price: $${(event.details.exit_price || event.details.price)?.toLocaleString()} | PnL: $${event.details.pnl?.toFixed(2)}`}
                                            {isPartial && `Price: $${event.details.price?.toLocaleString()} | Qty: ${event.details.quantity} | Remaining: ${event.details.remaining_qty}`}
                                            {isScaleIn && `Price: $${event.details.price?.toLocaleString()} | Qty: ${event.details.quantity} | Total: ${event.details.total_qty}`}
                                            {isLevelUpdate && (
                                                <>
                                                    {event.details.stop_loss && `SL: $${event.details.stop_loss.toLocaleString()} `}
                                                    {event.details.take_profit && `TP: $${event.details.take_profit.toLocaleString()} `}
                                                    {event.details.trailing_stop_percent && `TS: ${event.details.trailing_stop_percent}%`}
                                                </>
                                            )}
                                            {!isEntry && !isExit && !isPartial && !isScaleIn && !isLevelUpdate && JSON.stringify(event.details)}
                                            <div className="text-[9px] mt-1 opacity-50">
                                                {new Date(event.timestamp).toLocaleString(undefined, { timeZone: 'UTC' })}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })
                        ) : loadingEvents ? (
                            <div className="text-xs text-muted-foreground animate-pulse">Loading events...</div>
                        ) : (
                            <div className="text-xs text-muted-foreground">No detailed events available.</div>
                        )}
                    </div>
                </div>

                {/* Section 2: PnL Receipt */}
                <div className="space-y-4">
                    <h4 className="text-sm font-semibold text-primary uppercase tracking-wider flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-primary" />
                        PnL Receipt
                    </h4>
                    <div className="bg-background/40 p-4 border border-border rounded-md font-mono text-xs text-muted-foreground shadow-inner">
                        <div className="flex justify-between border-b border-border/30 pb-2 mb-2">
                            <span>ENTRY VALUE</span>
                            <span className="text-white">${entryValue.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between pb-1">
                            <span>EXIT VALUE</span>
                            <span className="text-white">${exitValue.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between pb-2 border-b border-border/30 mb-2 italic">
                            <span>(Gross PnL Calculation)</span>
                            <span className={(trade.gross_pnl ?? (exitValue - entryValue)) >= 0 ? "text-green-500" : "text-red-500"}>
                                ${(trade.gross_pnl ?? (exitValue - entryValue)).toFixed(2)}
                            </span>
                        </div>

                        <div className="space-y-1 mb-2">
                            <div className="flex justify-between">
                                <span>Entry Fee (Taker)</span>
                                <span>-${(trade.entry_commission || 0).toFixed(4)}</span>
                            </div>
                            <div className="flex justify-between">
                                <span>Exit Fee (Maker/Taker)</span>
                                <span>-${(trade.exit_commission || 0).toFixed(4)}</span>
                            </div>
                            <div className="flex justify-between">
                                <span>Funding Fee</span>
                                <span>-${(trade.funding_fee || 0).toFixed(4)}</span>
                            </div>
                            <div className="flex justify-between">
                                <span>Slippage Impact</span>
                                <span>-${(trade.slippage || 0).toFixed(4)}</span>
                            </div>
                        </div>

                        <div className="border-t-2 border-dashed border-border py-2 mt-4">
                            <div className="flex justify-between text-sm font-bold text-white uppercase">
                                <span>Net PnL</span>
                                <div className="text-right">
                                    <div className={(trade.net_pnl ?? trade.pnl) >= 0 ? "text-green-500" : "text-red-500"}>
                                        ${(trade.net_pnl ?? trade.pnl).toFixed(2)}
                                    </div>
                                    <div className="text-[10px] text-muted-foreground">({trade.pnl_percent.toFixed(2)}%)</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

interface PositionLogTableProps {
    trades: Trade[];
    backtestId: string;
}

export const PositionLogTable = React.memo(({ trades, backtestId }: PositionLogTableProps) => {
    const [sortColumn, setSortColumn] = useState<string | null>(null);
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
    const [page, setPage] = useState(1);
    const pageSize = 20;

    // Entry Reason Dialog State
    const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);

    // Sorting Logic
    const [expandedTradeId, setExpandedTradeId] = useState<string | null>(null);

    const toggleRow = (id: string) => {
        setExpandedTradeId(expandedTradeId === id ? null : id);
    };

    const sortedTrades = useMemo(() => {
        if (!sortColumn) return trades;

        return [...trades].sort((a, b) => {
            let aValue: any;
            let bValue: any;

            switch (sortColumn) {
                case 'side': aValue = a.side; bValue = b.side; break;
                case 'entry_time': aValue = new Date(a.entry_time).getTime(); bValue = new Date(b.entry_time).getTime(); break;
                case 'entry_price': aValue = a.entry_price; bValue = b.entry_price; break;
                case 'quantity': aValue = a.quantity; bValue = b.quantity; break;
                case 'exit_price': aValue = a.exit_price || 0; bValue = b.exit_price || 0; break;
                case 'pnl': aValue = a.pnl; bValue = b.pnl; break;
                case 'mae': aValue = a.mae || 0; bValue = b.mae || 0; break;
                case 'mfe': aValue = a.mfe || 0; bValue = b.mfe || 0; break;
                case 'symbol': aValue = a.symbol; bValue = b.symbol; break;
                // New Fee Columns
                case 'maker_fee': aValue = Number(a.maker_fee || 0); bValue = Number(b.maker_fee || 0); break;
                case 'taker_fee': aValue = Number(a.taker_fee || 0); bValue = Number(b.taker_fee || 0); break;
                case 'funding_fee': aValue = Number(a.funding_fee || 0); bValue = Number(b.funding_fee || 0); break;
                // Time Columns
                case 'exit_time': aValue = new Date(a.exit_time).getTime(); bValue = new Date(b.exit_time).getTime(); break;
                case 'duration':
                    aValue = new Date(a.exit_time).getTime() - new Date(a.entry_time).getTime();
                    bValue = new Date(b.exit_time).getTime() - new Date(b.entry_time).getTime();
                    break;
                case 'exit_reason':
                    // Sort by reason string (handle nulls)
                    aValue = (a.exit_reason?.reason || 'Unknown').toString().toLowerCase();
                    bValue = (b.exit_reason?.reason || 'Unknown').toString().toLowerCase();
                    break;
                case 'margin':
                    aValue = Number(a.entry_reason?.current_margin || a.entry_reason?.initial_margin || 0);
                    bValue = Number(b.entry_reason?.current_margin || b.entry_reason?.initial_margin || 0);
                    break;
                default:
                    // Fallback for generic keys if any
                    aValue = (a as any)[sortColumn];
                    bValue = (b as any)[sortColumn];
                    break;
            }

            if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
            if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
            return 0;
        });
    }, [trades, sortColumn, sortDirection]);

    // Pagination Logic
    const totalPages = Math.ceil(sortedTrades.length / pageSize);
    const paginatedTrades = useMemo(() => {
        const start = (page - 1) * pageSize;
        return sortedTrades.slice(start, start + pageSize);
    }, [sortedTrades, page, pageSize]);

    const handleSort = (column: string) => {
        if (sortColumn === column) {
            setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
        } else {
            setSortColumn(column);
            setSortDirection('asc');
        }
        setPage(1); // Reset page on sort
    };

    const exportCsv = () => {
        // Simple CSV Export logic (Client side)
        const headers = ['Entry Time', 'Symbol', 'Side', 'Entry Price', 'Exit Time', 'Exit Price', 'Duration', 'Size', 'MAE%', 'MFE%', 'PnL'];
        const rows = trades.map(t => {
            const durationMs = new Date(t.exit_time).getTime() - new Date(t.entry_time).getTime();
            const durationMinutes = Math.floor(durationMs / 60000); // Simple minutes
            // Better formatting for duration
            const hours = Math.floor(durationMinutes / 60);
            const minutes = durationMinutes % 60;
            const durationStr = `${hours > 0 ? `${hours}h ` : ''}${minutes}m`;

            return [
                t.entry_time, t.symbol, t.side, t.entry_price, t.exit_time, t.exit_price, durationStr, t.quantity, t.mae || 0, t.mfe || 0, t.pnl
            ]
        });
        const csvContent = "data:text/csv;charset=utf-8," +
            [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", "position_log.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const getExitReasonBadge = (reasonObj?: Record<string, any>) => {
        if (!reasonObj) return <Badge variant="outline" className="text-muted-foreground border-muted-foreground/30">Unknown</Badge>;

        const reason = (reasonObj.reason || '').toString();
        const upperReason = reason.toUpperCase();

        if (upperReason.includes('STOP LOSS') || upperReason.includes('STOP_LOSS') || upperReason.includes('SL')) {
            return <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/20 whitespace-nowrap">Stop Loss</Badge>;
        }
        if (upperReason.includes('TAKE PROFIT') || upperReason.includes('TAKE_PROFIT') || upperReason.includes('TP')) {
            return <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20 whitespace-nowrap">Take Profit</Badge>;
        }
        if (upperReason.includes('LIQUIDATION')) {
            return <Badge variant="outline" className="bg-orange-500/10 text-orange-500 border-orange-500/20 whitespace-nowrap">Liquidation</Badge>;
        }
        if (upperReason.includes('END OF BACKTEST')) {
            return <Badge variant="outline" className="bg-gray-500/10 text-gray-500 border-gray-500/20 whitespace-nowrap">End of Backtest</Badge>;
        }

        // Indicator/Signal (Blue)
        return <Badge variant="outline" className="bg-blue-500/10 text-blue-500 border-blue-500/20 whitespace-nowrap">Indicator</Badge>;
    };

    if (trades.length === 0) {
        return (
            <Card>
                <CardHeader><CardTitle>Position Log</CardTitle></CardHeader>
                <CardContent>
                    <div className="text-center py-8 text-muted-foreground">No trades available.</div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="border-border bg-card">
            <CardHeader className="flex flex-row items-center justify-between">
                <div>
                    <CardTitle>Position Log</CardTitle>
                    <CardDescription>Detailed history of all executed trades ({trades.length} items)</CardDescription>
                </div>
                <Button variant="outline" size="sm" onClick={exportCsv} className="gap-2">
                    <Download className="h-4 w-4" />
                    Export CSV
                </Button>
            </CardHeader>
            <CardContent>
                <div className="rounded-md border border-border">
                    <Table>
                        <TableHeader>
                            <TableRow className="border-border hover:bg-transparent">
                                <TableHead className="text-center w-[40px]"></TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-center" onClick={() => handleSort('side')}>
                                    Side {sortColumn === 'side' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer hover:text-primary" onClick={() => handleSort('entry_time')}>
                                    Entry Time {sortColumn === 'entry_time' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-right" onClick={() => handleSort('entry_price')}>
                                    Entry Price {sortColumn === 'entry_price' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-right" onClick={() => handleSort('exit_time')}>
                                    Exit Time {sortColumn === 'exit_time' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-right" onClick={() => handleSort('exit_price')}>
                                    Exit Price {sortColumn === 'exit_price' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-right" onClick={() => handleSort('duration')}>
                                    Duration {sortColumn === 'duration' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-right" onClick={() => handleSort('margin')}>
                                    Margin {sortColumn === 'margin' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-right" onClick={() => handleSort('quantity')}>
                                    {(() => {
                                        const hasStrategySizing = trades.some(t => t.entry_reason?.sizing_source === 'STRATEGY');
                                        const hasEngineSizing = trades.some(t => t.entry_reason?.sizing_source === 'ENGINE');

                                        let label = 'Size';
                                        if (hasStrategySizing && hasEngineSizing) label = 'Size (Mixed)';
                                        else if (hasStrategySizing) label = 'Size (Strategy)';
                                        else if (hasEngineSizing) label = 'Size (Default)';

                                        const arrow = sortColumn === 'quantity' ? (sortDirection === 'asc' ? ' ↑' : ' ↓') : '';
                                        return `${label}${arrow}`;
                                    })()}
                                </TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-right" onClick={() => handleSort('mae')}>
                                    <div className="flex items-center justify-end gap-1">
                                        MAE {sortColumn === 'mae' && (sortDirection === 'asc' ? '↑' : '↓')}
                                        <TooltipProvider>
                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <Info className="h-3 w-3 cursor-help text-muted-foreground" />
                                                </TooltipTrigger>
                                                <TooltipContent>
                                                    <p className="text-xs">Maximum Adverse Excursion (Leveraged ROI%)</p>
                                                </TooltipContent>
                                            </Tooltip>
                                        </TooltipProvider>
                                    </div>
                                </TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-right" onClick={() => handleSort('mfe')}>
                                    <div className="flex items-center justify-end gap-1">
                                        MFE {sortColumn === 'mfe' && (sortDirection === 'asc' ? '↑' : '↓')}
                                        <TooltipProvider>
                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <Info className="h-3 w-3 cursor-help text-muted-foreground" />
                                                </TooltipTrigger>
                                                <TooltipContent>
                                                    <p className="text-xs">Maximum Favorable Excursion (Leveraged ROI%)</p>
                                                </TooltipContent>
                                            </Tooltip>
                                        </TooltipProvider>
                                    </div>
                                </TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-right" onClick={() => handleSort('pnl')}>
                                    PnL {sortColumn === 'pnl' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-right" onClick={() => handleSort('maker_fee')}>
                                    Maker Fee {sortColumn === 'maker_fee' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-right" onClick={() => handleSort('taker_fee')}>
                                    Taker Fee {sortColumn === 'taker_fee' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-right" onClick={() => handleSort('funding_fee')}>
                                    Funding {sortColumn === 'funding_fee' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-center" onClick={() => handleSort('exit_reason')}>
                                    Reason {sortColumn === 'exit_reason' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="text-center w-[80px]">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {paginatedTrades.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={20} className="text-center py-8 text-muted-foreground">
                                        No trades recorded yet.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                paginatedTrades.map((trade) => {
                                    // Calculate duration for display
                                    // Parse ISO dates
                                    const entryDate = new Date(trade.entry_time);
                                    const exitDate = new Date(trade.exit_time);
                                    const durationMs = exitDate.getTime() - entryDate.getTime();
                                    const durationSec = Math.floor(durationMs / 1000);

                                    let durationStr = `${durationSec}s`;
                                    if (durationSec > 60) {
                                        const mins = Math.floor(durationSec / 60);
                                        durationStr = `${mins}m ${durationSec % 60}s`;
                                        if (mins > 60) {
                                            const hours = Math.floor(mins / 60);
                                            durationStr = `${hours}h ${mins % 60}m`;
                                        }
                                    }

                                    const isWin = trade.pnl > 0;
                                    const isExpanded = expandedTradeId === trade.trade_id;

                                    return (
                                        <React.Fragment key={trade.trade_id || Math.random()}>
                                            <TableRow
                                                className={cn(
                                                    "border-border cursor-pointer transition-colors",
                                                    isExpanded ? "bg-muted/40" : "hover:bg-muted/50"
                                                )}
                                                onClick={() => toggleRow(trade.trade_id)}
                                            >
                                                <TableCell className="text-center text-muted-foreground">
                                                    <div className={cn("transition-transform duration-200", isExpanded ? "rotate-90" : "")}>
                                                        ▶
                                                    </div>
                                                </TableCell>
                                                <TableCell className="text-center">
                                                    <Badge
                                                        variant="secondary"
                                                        className={cn(
                                                            "font-mono text-xs uppercase w-16 justify-center",
                                                            (trade.side?.toLowerCase() === 'long' || trade.side?.toLowerCase() === 'buy') ? "bg-green-500/10 text-green-500 border-green-500/20" : "bg-red-500/10 text-red-500 border-red-500/20"
                                                        )}
                                                    >
                                                        {(trade.side?.toLowerCase()) === 'long' || trade.side?.toLowerCase() === 'buy' ? 'LONG' : 'SHORT'}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell className="font-mono text-xs text-white whitespace-nowrap">
                                                    {entryDate.toLocaleString(undefined, { timeZone: 'UTC' })}
                                                </TableCell>
                                                <TableCell className="text-right font-mono text-xs">
                                                    {(() => {
                                                        const hasScaledIn = trade.initial_entry_price && trade.initial_entry_price !== trade.entry_price;
                                                        if (hasScaledIn) {
                                                            return (
                                                                <>
                                                                    ${trade.initial_entry_price!.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })}
                                                                    <span className="text-muted-foreground"> (${trade.entry_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })})</span>
                                                                </>
                                                            );
                                                        }
                                                        return `$${trade.entry_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })}`;
                                                    })()}
                                                </TableCell>
                                                <TableCell className="text-right font-mono text-xs text-white whitespace-nowrap">
                                                    {exitDate.toLocaleString(undefined, { timeZone: 'UTC' })}
                                                </TableCell>
                                                <TableCell className="text-right font-mono text-xs">
                                                    ${trade.exit_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })}
                                                </TableCell>
                                                <TableCell className="text-right font-mono text-xs text-white">
                                                    {durationStr}
                                                </TableCell>
                                                <TableCell className="text-right font-mono text-xs">
                                                    {(() => {
                                                        const initialMargin = trade.entry_reason?.initial_margin;
                                                        const currentMargin = trade.entry_reason?.current_margin;

                                                        if (initialMargin !== undefined && currentMargin !== undefined) {
                                                            const hasChanged = Math.abs(initialMargin - currentMargin) > 0.000001;
                                                            if (hasChanged) {
                                                                return (
                                                                    <>
                                                                        ${initialMargin.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                                                        <span className="text-muted-foreground"> (${currentMargin.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })})</span>
                                                                    </>
                                                                );
                                                            }
                                                            return `$${initialMargin.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                                                        }

                                                        // Fallback for old backtests: calculate from exit pnl/leverage if available, 
                                                        // but simpler to just show '-' if data missing
                                                        return '-';
                                                    })()}
                                                </TableCell>
                                                <TableCell className="text-right font-mono text-xs">
                                                    {(() => {
                                                        const hasScaledIn = trade.initial_entry_quantity && trade.initial_entry_quantity !== trade.quantity;
                                                        if (hasScaledIn) {
                                                            return (
                                                                <>
                                                                    {trade.initial_entry_quantity!.toFixed(8)}
                                                                    <span className="text-muted-foreground"> ({trade.quantity.toFixed(8)})</span>
                                                                </>
                                                            );
                                                        }
                                                        return trade.quantity.toFixed(8);
                                                    })()}
                                                </TableCell>
                                                <TableCell className="text-right font-mono text-xs text-red-500">
                                                    {trade.mae ? `${trade.mae.toFixed(2)}%` : '0.00%'}
                                                </TableCell>
                                                <TableCell className="text-right font-mono text-xs text-green-500">
                                                    {trade.mfe ? `${trade.mfe.toFixed(2)}%` : '0.00%'}
                                                </TableCell>
                                                <TableCell className={cn("text-right font-bold font-mono text-xs", isWin ? "text-green-500" : "text-red-500")}>
                                                    ${trade.pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                                    <div className="text-[10px] opacity-70">{trade.pnl_percent.toFixed(2)}%</div>
                                                </TableCell>
                                                <TableCell className={cn("text-right font-mono text-xs", (trade.maker_fee || 0) !== 0 ? "text-[#EEA727]" : "text-white")}>
                                                    ${(trade.maker_fee || 0).toFixed(4)}
                                                </TableCell>
                                                <TableCell className={cn("text-right font-mono text-xs", (trade.taker_fee || 0) !== 0 ? "text-[#EEA727]" : "text-white")}>
                                                    ${(trade.taker_fee || 0).toFixed(4)}
                                                </TableCell>
                                                <TableCell className={cn("text-right font-mono text-xs", (trade.funding_fee || 0) !== 0 ? "text-[#EEA727]" : "text-white")}>
                                                    ${(trade.funding_fee || 0).toFixed(4)}
                                                </TableCell>
                                                <TableCell className="text-center">
                                                    {getExitReasonBadge(trade.exit_reason)}
                                                </TableCell>
                                                <TableCell className="text-center">
                                                    <Button
                                                        variant="ghost"
                                                        size="icon"
                                                        className="h-8 w-8 text-muted-foreground hover:text-primary"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            setSelectedTrade(trade);
                                                        }}
                                                    >
                                                        <Eye className="h-4 w-4" />
                                                    </Button>
                                                </TableCell>
                                            </TableRow>
                                            {isExpanded && (
                                                <TableRow className="border-border hover:bg-transparent bg-muted/10">
                                                    <TableCell colSpan={20} className="p-0">
                                                        <PnLReceipt trade={trade} backtestId={backtestId} />
                                                    </TableCell>
                                                </TableRow>
                                            )}
                                        </React.Fragment>
                                    );
                                })
                            )}
                        </TableBody>
                    </Table>
                </div>
                {/* Pagination Controls could be added here */}
                <div className="flex justify-end p-2 gap-2">
                    <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Previous</Button>
                    <span className="text-sm py-2 px-2 text-muted-foreground">Page {page} of {totalPages || 1}</span>
                    <Button variant="outline" size="sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages || totalPages === 0}>Next</Button>
                </div>
            </CardContent>

            <Dialog open={!!selectedTrade} onOpenChange={(open) => !open && setSelectedTrade(null)}>
                <DialogContent className="max-w-[600px] max-h-[80vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>Trade Entry Details</DialogTitle>
                        <DialogDescription>
                            Technical conditions triggering this {selectedTrade?.side} position on {selectedTrade?.symbol}
                        </DialogDescription>
                    </DialogHeader>
                    {selectedTrade && (
                        <div className="space-y-4 py-4">
                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div className="space-y-1">
                                    <Label className="text-muted-foreground">Entry Time</Label>
                                    <p className="font-mono">{new Date(selectedTrade.entry_time).toLocaleString()}</p>
                                </div>
                                <div className="space-y-1">
                                    <Label className="text-muted-foreground">Entry Price</Label>
                                    <p className="font-mono">${selectedTrade.entry_price}</p>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label>Entry Reason & Indicators</Label>
                                {selectedTrade.entry_reason ? (
                                    <div className="bg-muted/50 p-4 rounded-md overflow-x-auto border border-border">
                                        <pre className="text-xs font-mono">
                                            {JSON.stringify(selectedTrade.entry_reason, null, 2)}
                                        </pre>
                                    </div>
                                ) : (
                                    <div className="bg-muted/20 p-4 rounded-md text-center text-muted-foreground text-xs border border-dashed">
                                        No entry metadata.
                                    </div>
                                )}
                            </div>

                            <div className="space-y-2">
                                <Label>Exit Reason & Indicators</Label>
                                {selectedTrade.exit_reason ? (
                                    <div className="bg-muted/50 p-4 rounded-md overflow-x-auto border border-border">
                                        <pre className="text-xs font-mono">
                                            {JSON.stringify(selectedTrade.exit_reason, null, 2)}
                                        </pre>
                                    </div>
                                ) : (
                                    <div className="bg-muted/20 p-4 rounded-md text-center text-muted-foreground text-xs border border-dashed">
                                        No exit metadata.
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </Card>
    );
});

PositionLogTable.displayName = 'PositionLogTable';
