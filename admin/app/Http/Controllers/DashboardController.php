<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Carbon\Carbon;

class DashboardController extends Controller
{
    /**
     * Show the application dashboard with analytics.
     *
     * @return \Illuminate\Contracts\Support\Renderable
     */
    public function index()
    {
        $now = Carbon::now();
        $thirtyDaysAgo = $now->copy()->subDays(30);

        // ── Summary cards ──────────────────────────────────────────────
        $totalUsers = DB::table('users')
            ->where('user_type', 'user')
            ->where('status', 1)
            ->count();

        $totalRevenue = DB::table('payments')
            ->selectRaw('SUM(CAST(amount AS DECIMAL(10,2))) as total')
            ->value('total') ?? 0;

        $activeSubscribers = DB::table('users')
            ->where('user_type', 'user')
            ->where('status', 1)
            ->where('subscription_id', '>', 0)
            ->count();

        // Tip win rate across all tip tables
        $tipResults = collect(['tips', 'free_tips', 'another_tips'])
            ->map(function ($table) {
                return DB::table($table)
                    ->selectRaw("
                        SUM(CASE WHEN LOWER(result) = 'won' THEN 1 ELSE 0 END) as won,
                        SUM(CASE WHEN LOWER(result) = 'lost' THEN 1 ELSE 0 END) as lost,
                        SUM(CASE WHEN LOWER(result) NOT IN ('won','lost') OR result IS NULL THEN 1 ELSE 0 END) as pending,
                        COUNT(*) as total
                    ")
                    ->first();
            })
            ->reduce(function ($carry, $item) {
                $carry['won'] += $item->won ?? 0;
                $carry['lost'] += $item->lost ?? 0;
                $carry['pending'] += $item->pending ?? 0;
                $carry['total'] += $item->total ?? 0;
                return $carry;
            }, ['won' => 0, 'lost' => 0, 'pending' => 0, 'total' => 0]);

        $decidedTips = $tipResults['won'] + $tipResults['lost'];
        $tipWinRate = $decidedTips > 0
            ? round(($tipResults['won'] / $decidedTips) * 100, 1)
            : 0;

        // ── User growth (last 30 days) ─────────────────────────────────
        $userGrowth = DB::table('users')
            ->where('user_type', 'user')
            ->where('created_at', '>=', $thirtyDaysAgo)
            ->selectRaw('DATE(created_at) as date, COUNT(*) as count')
            ->groupBy('date')
            ->orderBy('date')
            ->get()
            ->pluck('count', 'date');

        // Fill missing days with 0
        $userGrowthLabels = [];
        $userGrowthData = [];
        for ($i = 30; $i >= 0; $i--) {
            $date = $now->copy()->subDays($i)->format('Y-m-d');
            $userGrowthLabels[] = $now->copy()->subDays($i)->format('M d');
            $userGrowthData[] = $userGrowth[$date] ?? 0;
        }

        // ── Revenue (last 30 days) ─────────────────────────────────────
        $revenue = DB::table('payments')
            ->where('created_at', '>=', $thirtyDaysAgo)
            ->selectRaw('DATE(created_at) as date, SUM(CAST(amount AS DECIMAL(10,2))) as total')
            ->groupBy('date')
            ->orderBy('date')
            ->get()
            ->pluck('total', 'date');

        $revenueLabels = [];
        $revenueData = [];
        for ($i = 30; $i >= 0; $i--) {
            $date = $now->copy()->subDays($i)->format('Y-m-d');
            $revenueLabels[] = $now->copy()->subDays($i)->format('M d');
            $revenueData[] = (float)($revenue[$date] ?? 0);
        }

        // ── Platform distribution ──────────────────────────────────────
        $platforms = DB::table('payments')
            ->selectRaw('platform, COUNT(*) as count')
            ->groupBy('platform')
            ->get();

        $platformLabels = $platforms->pluck('platform')->map(function ($p) {
            return ucfirst($p ?: 'Unknown');
        })->toArray();
        $platformData = $platforms->pluck('count')->toArray();

        // ── Subscription distribution ──────────────────────────────────
        $subDistribution = DB::table('users')
            ->where('user_type', 'user')
            ->where('status', 1)
            ->leftJoin('subscriptions', 'users.subscription_id', '=', 'subscriptions.id')
            ->selectRaw("
                CASE WHEN users.subscription_id = 0 OR users.subscription_id IS NULL
                     THEN 'Free User'
                     ELSE COALESCE(subscriptions.name, 'Unknown')
                END as plan_name,
                COUNT(*) as count
            ")
            ->groupBy('plan_name')
            ->get();

        $subLabels = $subDistribution->pluck('plan_name')->toArray();
        $subData = $subDistribution->pluck('count')->toArray();

        // ── Recent payments ────────────────────────────────────────────
        $recentPayments = DB::table('payments')
            ->leftJoin('users', 'payments.user_id', '=', 'users.id')
            ->leftJoin('subscriptions', 'payments.subscription_id', '=', 'subscriptions.id')
            ->select(
                'payments.amount',
                'payments.platform',
                'payments.created_at',
                DB::raw("CONCAT(users.first_name, ' ', users.last_name) as user_name"),
                'subscriptions.name as plan_name'
            )
            ->orderBy('payments.created_at', 'desc')
            ->limit(10)
            ->get();

        // ── New users today / this week ────────────────────────────────
        $newUsersToday = DB::table('users')
            ->where('user_type', 'user')
            ->whereDate('created_at', $now->toDateString())
            ->count();

        $newUsersThisWeek = DB::table('users')
            ->where('user_type', 'user')
            ->where('created_at', '>=', $now->copy()->startOfWeek())
            ->count();

        return view('backend.dashboard', compact(
            'totalUsers',
            'totalRevenue',
            'activeSubscribers',
            'tipWinRate',
            'tipResults',
            'userGrowthLabels',
            'userGrowthData',
            'revenueLabels',
            'revenueData',
            'platformLabels',
            'platformData',
            'subLabels',
            'subData',
            'recentPayments',
            'newUsersToday',
            'newUsersThisWeek'
        ));
    }
}
