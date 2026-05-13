<table class="table table-bordered">

    <tr>
        <td>{{ _lang('User') }}</td>
        <td>{{ $payment->user->name }}</td>
    </tr>
    <tr>
        <td>{{ _lang('Subscription') }}</td>
        <td>{{ $payment->subscription->name }}</td>
    </tr>
    <tr>
        <td>{{ _lang('Amount($)') }}</td>
        <td>{{ $payment->amount }}</td>
    </tr>
    <tr>
        <td>{{ _lang('Date') }}</td>
        <td>{{ date("d F, Y H:i:s", strtotime($payment->date)) }}</td>
    </tr>
    <tr>
        <td>{{ _lang('Platform') }}</td>
        <td>{{ strtoupper($payment->platform) }}</td>
    </tr>

</table>
