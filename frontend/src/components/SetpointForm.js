// src/components/SetpointForm.js
import React from 'react';

function SetpointForm({setpoint, setSetpoint, message, setMessage}) {
    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            const response = await fetch('/api/temperature/setpoint', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({setpoint: Number(setpoint)}),
            });
            const result = await response.json();
            if (response.ok) {
                setMessage(`设定值更新成功：${result.setpoint}`);
            } else {
                setMessage('更新失败: ' + (result.error || '未知错误'));
            }
        } catch (error) {
            setMessage('请求错误: ' + error.message);
        }
    };

    return (
        <form onSubmit={handleSubmit}>
            <label>
                当前目标值:
                <input
                    type="number"
                    value={setpoint}
                    onChange={(e) => setSetpoint(Number(e.target.value))}
                    style={{width: '100%', padding: '0.5rem', marginTop: '0.5rem', marginBottom: '1rem'}}
                />
            </label>
            <button type="submit" style={{padding: '0.5rem 1rem'}}>更新目标值</button>
            {message && <p style={{marginTop: '1rem', color: 'green'}}>{message}</p>}
        </form>
    );
}

export default SetpointForm;
