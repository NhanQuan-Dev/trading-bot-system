import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

export default function BacktestDetailTest() {
    const { id } = useParams();
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        console.log('🔍 TEST: Component mounted, ID:', id);
        console.log('🔍 TEST: Loading state:', loading);

        const fetchData = async () => {
            console.log('🔍 TEST: Starting fetch...');
            try {
                const response = await fetch(`/api/v1/backtests/${id}`);
                console.log('🔍 TEST: Response status:', response.status);
                const result = await response.json();
                console.log('🔍 TEST: Data received:', result);
                setData(result);
                console.log('🔍 TEST: Setting loading to FALSE');
                setLoading(false);
                console.log('🔍 TEST: Loading should be false now');
            } catch (error) {
                console.error('🔍 TEST: Error:', error);
                setLoading(false);
            }
        };

        fetchData();
    }, [id]);

    console.log('🔍 TEST: Rendering, loading =', loading, 'data =', !!data);

    if (loading) {
        return (
            <DashboardLayout>
                <div className="p-8">
                    <h1 className="text-2xl font-bold mb-4">TEST PAGE - LOADING...</h1>
                    <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent"></div>
                    <p className="mt-4">Check console for debug logs (F12)</p>
                </div>
            </DashboardLayout>
        );
    }

    return (
        <DashboardLayout>
            <div className="p-8">
                <h1 className="text-2xl font-bold mb-4">TEST PAGE - DATA LOADED! ✅</h1>
                <div className="bg-green-100 p-4 rounded">
                    <p>Loading completed successfully!</p>
                    <p className="mt-2">Backtest ID: {id}</p>
                    <p>Status: {data?.status}</p>
                </div>
                <pre className="mt-4 bg-gray-100 p-4 rounded text-xs overflow-auto">
                    {JSON.stringify(data, null, 2)}
                </pre>
            </div>
        </DashboardLayout>
    );
}
