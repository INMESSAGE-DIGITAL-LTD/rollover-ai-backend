@extends('layouts.app')

@section('content')
{{-- ── Row 1: Summary Cards ─────────────────────────────────────────── --}}
<div class="row">
    <div class="col-sm-6 col-xl-3 mb-4">
        <div class="card border-0 shadow-sm">
            <div class="card-body">
                <div class="d-flex align-items-center justify-content-between mb-2">
                    <span class="h6 text-muted text-uppercase mb-0">Total Users</span>
                    <span class="badge badge-soft-primary rounded-pill" style="background:#e8f0fe;color:#2972fa;">
                        <i class="fa fa-users"></i>
                    </span>
                </div>
                <span class="h2 mb-0 d-block">{{ number_format($totalUsers) }}</span>
                <small class="text-muted">
                    <i class="fa fa-arrow-up text-success"></i>
                    {{ $newUsersToday }} today &middot; {{ $newUsersThisWeek }} this week
                </small>
            </div>
        </div>
    </div>

    <div class="col-sm-6 col-xl-3 mb-4">
        <div class="card border-0 shadow-sm">
            <div class="card-body">
                <div class="d-flex align-items-center justify-content-between mb-2">
                    <span class="h6 text-muted text-uppercase mb-0">Total Revenue</span>
                    <span class="badge badge-soft-success rounded-pill" style="background:#e6f9ee;color:#0dd157;">
                        <i class="fa fa-dollar-sign"></i>
                    </span>
                </div>
                <span class="h2 mb-0 d-block">${{ number_format($totalRevenue, 2) }}</span>
                <small class="text-muted">All time</small>
            </div>
        </div>
    </div>

    <div class="col-sm-6 col-xl-3 mb-4">
        <div class="card border-0 shadow-sm">
            <div class="card-body">
                <div class="d-flex align-items-center justify-content-between mb-2">
                    <span class="h6 text-muted text-uppercase mb-0">Tips Win Rate</span>
                    <span class="badge badge-soft-warning rounded-pill" style="background:#fff8e6;color:#fab633;">
                        <i class="fa fa-chart-pie"></i>
                    </span>
                </div>
                <span class="h2 mb-0 d-block">{{ $tipWinRate }}%</span>
                <small class="text-muted">
                    {{ $tipResults['won'] }} won &middot; {{ $tipResults['lost'] }} lost &middot; {{ $tipResults['pending'] }} pending
                </small>
            </div>
        </div>
    </div>

    <div class="col-sm-6 col-xl-3 mb-4">
        <div class="card border-0 shadow-sm">
            <div class="card-body">
                <div class="d-flex align-items-center justify-content-between mb-2">
                    <span class="h6 text-muted text-uppercase mb-0">Active Subscribers</span>
                    <span class="badge badge-soft-danger rounded-pill" style="background:#fde8e8;color:#fb4143;">
                        <i class="fa fa-crown"></i>
                    </span>
                </div>
                <span class="h2 mb-0 d-block">{{ number_format($activeSubscribers) }}</span>
                <small class="text-muted">
                    @if($totalUsers > 0)
                        {{ round(($activeSubscribers / $totalUsers) * 100, 1) }}% of all users
                    @else
                        No users yet
                    @endif
                </small>
            </div>
        </div>
    </div>
</div>

{{-- ── Row 2: User Growth + Subscription Distribution ───────────────── --}}
<div class="row">
    <div class="col-xl-8 mb-4">
        <div class="card border-0 shadow-sm h-100">
            <div class="card-header bg-white border-0 pb-0">
                <h6 class="text-uppercase text-muted mb-0">User Growth <small class="text-muted">(Last 30 Days)</small></h6>
            </div>
            <div class="card-body">
                <canvas id="userGrowthChart" height="280"></canvas>
            </div>
        </div>
    </div>
    <div class="col-xl-4 mb-4">
        <div class="card border-0 shadow-sm h-100">
            <div class="card-header bg-white border-0 pb-0">
                <h6 class="text-uppercase text-muted mb-0">Subscription Plans</h6>
            </div>
            <div class="card-body d-flex align-items-center justify-content-center">
                <canvas id="subDistChart" height="260"></canvas>
            </div>
        </div>
    </div>
</div>

{{-- ── Row 3: Revenue + Platform Distribution ────────────────────────── --}}
<div class="row">
    <div class="col-xl-8 mb-4">
        <div class="card border-0 shadow-sm h-100">
            <div class="card-header bg-white border-0 pb-0">
                <h6 class="text-uppercase text-muted mb-0">Revenue <small class="text-muted">(Last 30 Days)</small></h6>
            </div>
            <div class="card-body">
                <canvas id="revenueChart" height="280"></canvas>
            </div>
        </div>
    </div>
    <div class="col-xl-4 mb-4">
        <div class="card border-0 shadow-sm h-100">
            <div class="card-header bg-white border-0 pb-0">
                <h6 class="text-uppercase text-muted mb-0">Payment Platforms</h6>
            </div>
            <div class="card-body d-flex align-items-center justify-content-center">
                <canvas id="platformChart" height="260"></canvas>
            </div>
        </div>
    </div>
</div>

{{-- ── Row 4: Tip Performance + Recent Payments ──────────────────────── --}}
<div class="row">
    <div class="col-xl-4 mb-4">
        <div class="card border-0 shadow-sm h-100">
            <div class="card-header bg-white border-0 pb-0">
                <h6 class="text-uppercase text-muted mb-0">Tip Performance</h6>
            </div>
            <div class="card-body d-flex align-items-center justify-content-center">
                <canvas id="tipPerfChart" height="260"></canvas>
            </div>
        </div>
    </div>
    <div class="col-xl-8 mb-4">
        <div class="card border-0 shadow-sm h-100">
            <div class="card-header bg-white border-0 pb-0">
                <h6 class="text-uppercase text-muted mb-0">Recent Payments</h6>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover mb-0">
                        <thead class="thead-light">
                            <tr>
                                <th class="border-0 pl-4">User</th>
                                <th class="border-0">Plan</th>
                                <th class="border-0">Amount</th>
                                <th class="border-0">Platform</th>
                                <th class="border-0 pr-4">Date</th>
                            </tr>
                        </thead>
                        <tbody>
                            @forelse($recentPayments as $payment)
                            <tr>
                                <td class="pl-4">{{ $payment->user_name ?? 'Unknown' }}</td>
                                <td>{{ $payment->plan_name ?? 'N/A' }}</td>
                                <td><strong>${{ number_format((float)$payment->amount, 2) }}</strong></td>
                                <td>
                                    <span class="badge badge-{{ $payment->platform === 'ios' ? 'dark' : ($payment->platform === 'android' ? 'success' : 'secondary') }}">
                                        {{ ucfirst($payment->platform ?? 'N/A') }}
                                    </span>
                                </td>
                                <td class="text-muted pr-4">{{ \Carbon\Carbon::parse($payment->created_at)->format('M d, Y') }}</td>
                            </tr>
                            @empty
                            <tr>
                                <td colspan="5" class="text-center text-muted py-4">No payments recorded yet</td>
                            </tr>
                            @endforelse
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>
@endsection

@section('js-script')
<script src="{{ asset('public/backend') }}/vendor/chart.js/dist/Chart.min.js"></script>
<script>
Chart.defaults.global.defaultFontFamily = "'Open Sans', sans-serif";
Chart.defaults.global.defaultFontColor = '#8898aa';

// ── User Growth (Line Chart) ──────────────────────────────────────
new Chart(document.getElementById('userGrowthChart').getContext('2d'), {
    type: 'line',
    data: {
        labels: @json($userGrowthLabels),
        datasets: [{
            label: 'New Users',
            data: @json($userGrowthData),
            borderColor: '#2972fa',
            backgroundColor: 'rgba(41,114,250,0.08)',
            borderWidth: 2.5,
            pointRadius: 0,
            pointHitRadius: 10,
            pointHoverRadius: 5,
            pointHoverBackgroundColor: '#2972fa',
            fill: true,
            tension: 0.4
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        legend: { display: false },
        scales: {
            xAxes: [{
                gridLines: { display: false },
                ticks: {
                    maxTicksLimit: 8,
                    maxRotation: 0
                }
            }],
            yAxes: [{
                gridLines: { borderDash: [5, 5], color: '#f0f0f0' },
                ticks: {
                    beginAtZero: true,
                    precision: 0
                }
            }]
        },
        tooltips: {
            mode: 'index',
            intersect: false,
            backgroundColor: '#333',
            titleFontSize: 12,
            bodyFontSize: 13,
            cornerRadius: 6
        }
    }
});

// ── Revenue (Bar Chart) ────────────────────────────────────────────
new Chart(document.getElementById('revenueChart').getContext('2d'), {
    type: 'bar',
    data: {
        labels: @json($revenueLabels),
        datasets: [{
            label: 'Revenue ($)',
            data: @json($revenueData),
            backgroundColor: '#0dd157',
            borderRadius: 4,
            barPercentage: 0.6
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        legend: { display: false },
        scales: {
            xAxes: [{
                gridLines: { display: false },
                ticks: {
                    maxTicksLimit: 8,
                    maxRotation: 0
                }
            }],
            yAxes: [{
                gridLines: { borderDash: [5, 5], color: '#f0f0f0' },
                ticks: {
                    beginAtZero: true,
                    callback: function(v) { return '$' + v; }
                }
            }]
        },
        tooltips: {
            callbacks: {
                label: function(item) { return '$' + item.yLabel.toFixed(2); }
            },
            backgroundColor: '#333',
            cornerRadius: 6
        }
    }
});

// ── Subscription Distribution (Doughnut) ───────────────────────────
var subLabels = @json($subLabels);
var subData = @json($subData);
if (subLabels.length > 0) {
    new Chart(document.getElementById('subDistChart').getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: subLabels,
            datasets: [{
                data: subData,
                backgroundColor: ['#2972fa', '#0dd157', '#fab633', '#fb4143', '#8b5cf6', '#06b6d4', '#f97316', '#ec4899'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutoutPercentage: 65,
            legend: {
                position: 'bottom',
                labels: { boxWidth: 12, padding: 12, fontSize: 12 }
            },
            tooltips: { backgroundColor: '#333', cornerRadius: 6 }
        }
    });
} else {
    document.getElementById('subDistChart').parentNode.innerHTML = '<p class="text-muted text-center">No data yet</p>';
}

// ── Platform Distribution (Doughnut) ───────────────────────────────
var platLabels = @json($platformLabels);
var platData = @json($platformData);
if (platLabels.length > 0) {
    new Chart(document.getElementById('platformChart').getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: platLabels,
            datasets: [{
                data: platData,
                backgroundColor: ['#333', '#0dd157', '#2972fa', '#fab633', '#fb4143'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutoutPercentage: 65,
            legend: {
                position: 'bottom',
                labels: { boxWidth: 12, padding: 12, fontSize: 12 }
            },
            tooltips: { backgroundColor: '#333', cornerRadius: 6 }
        }
    });
} else {
    document.getElementById('platformChart').parentNode.innerHTML = '<p class="text-muted text-center">No data yet</p>';
}

// ── Tip Performance (Doughnut) ─────────────────────────────────────
var tipData = @json([$tipResults['won'], $tipResults['lost'], $tipResults['pending']]);
if (tipData[0] + tipData[1] + tipData[2] > 0) {
    new Chart(document.getElementById('tipPerfChart').getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['Won', 'Lost', 'Pending'],
            datasets: [{
                data: tipData,
                backgroundColor: ['#0dd157', '#fb4143', '#fab633'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutoutPercentage: 65,
            legend: {
                position: 'bottom',
                labels: { boxWidth: 12, padding: 12, fontSize: 12 }
            },
            tooltips: { backgroundColor: '#333', cornerRadius: 6 }
        }
    });
} else {
    document.getElementById('tipPerfChart').parentNode.innerHTML = '<p class="text-muted text-center">No tips yet</p>';
}
</script>
@endsection
