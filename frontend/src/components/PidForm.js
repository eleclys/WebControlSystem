// src/components/PidForm.js
import React from 'react';

function PidForm({Kp, Ki, Kd, setKp, setKi, setKd, pidMessage, setPidMessage}) {
    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            const response = await fetch('/api/controller/params', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({Kp, Ki, Kd}),
            });
            const result = await response.json();
            if (response.ok) {
                setPidMessage(`PID 参数更新成功: Kp=${result.Kp}, Ki=${result.Ki}, Kd=${result.Kd}`);
            } else {
                setPidMessage('PID 更新失败: ' + (result.error || '未知错误'));
            }
        } catch (error) {
            setPidMessage('请求错误: ' + error.message);
        }
    };

    return (
        <form onSubmit={handleSubmit}>
            <h3>PID 参数设置</h3>
            <label>
                Kp:
                <input
                    type="number"
                    step="0.01"
                    value={Kp}
                    onChange={(e) => setKp(Number(e.target.value))}
                    style={{width: '100%', padding: '0.5rem', marginBottom: '1rem'}}
                />
            </label>
            <label>
                Ki:
                <input
                    type="number"
                    step="0.01"
                    value={Ki}
                    onChange={(e) => setKi(Number(e.target.value))}
                    style={{width: '100%', padding: '0.5rem', marginBottom: '1rem'}}
                />
            </label>
            <label>
                Kd:
                <input
                    type="number"
                    step="0.01"
                    value={Kd}
                    onChange={(e) => setKd(Number(e.target.value))}
                    style={{width: '100%', padding: '0.5rem', marginBottom: '1rem'}}
                />
            </label>
            <button type="submit" style={{padding: '0.5rem 1rem'}}>更新 PID 参数</button>
            {pidMessage && <p style={{marginTop: '1rem', color: 'blue'}}>{pidMessage}</p>}
        </form>
    );
}

export default PidForm;
