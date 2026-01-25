import tensorflow as tf


def cholesky_bootstrap_returns_tf(n: int, s: int, cov_matrix: tf.Tensor, exp_ret: tf.Tensor, seed: int = 42) -> tf.Tensor:
    """
    TensorFlow equivalent of numpy cholesky-based return simulation.

    Inputs mirror the numpy version, but use tensors:
    - cov_matrix: [k, k] covariance matrix (tf.float64)
    - exp_ret: [k] expected returns (tf.float64)

    Returns: [n, s, k] simulated returns
    """
    # NOTE: use tf.random.Generator for determinism in-graph.
    dtype = tf.float64
    cov_matrix = tf.convert_to_tensor(cov_matrix, dtype=dtype)
    exp_ret = tf.reshape(tf.convert_to_tensor(exp_ret, dtype=dtype), [-1])
    k = tf.shape(exp_ret)[0]

    chol = tf.linalg.cholesky(cov_matrix)
    gen = tf.random.Generator.from_seed(seed)
    z = gen.normal(shape=(n, s, k), dtype=dtype)
    correlated = tf.linalg.matmul(z, tf.transpose(chol))
    returns = correlated + exp_ret
    return returns


def simulate_wealth_tf(
    simulated_returns: tf.Tensor,
    weights: tf.Tensor,
    initial_wealth: float,
    cashflows: tf.Tensor,
    transactions: tf.Tensor,
    inflation: float = 0.03,
    time_steps: tf.Tensor | None = None,
) -> tf.Tensor:
    """
    TF equivalent of simulate_wealth. All math in TF to keep graph differentiable.
    Returns: wealth [n, s+1]
    """
    dtype = tf.float64
    simulated_returns = tf.convert_to_tensor(simulated_returns, dtype=dtype)
    weights = tf.convert_to_tensor(weights, dtype=dtype)
    cashflows = tf.convert_to_tensor(cashflows, dtype=dtype)
    transactions = tf.convert_to_tensor(transactions, dtype=dtype)
    init_w = tf.cast(initial_wealth, dtype)
    if time_steps is None:
        s = tf.shape(simulated_returns)[1]
        time_steps = tf.cast(tf.range(0, s + 1), dtype)
    else:
        time_steps = tf.convert_to_tensor(time_steps, dtype=dtype)

    n = tf.shape(simulated_returns)[0]
    s = tf.shape(simulated_returns)[1]
    k = tf.shape(simulated_returns)[2]

    tf.debugging.assert_equal(tf.shape(weights)[0], s, message="weights first dim must equal s")
    tf.debugging.assert_equal(tf.shape(weights)[1], k, message="weights second dim must equal k")
    tf.debugging.assert_equal(tf.shape(cashflows)[0], s, message="cashflows length must equal s")
    tf.debugging.assert_equal(tf.shape(transactions)[0], s, message="transactions length must equal s")
    tf.debugging.assert_equal(tf.shape(time_steps)[0], s + 1, message="time_steps length must equal s+1")

    time_delta = time_steps[1:] - time_steps[:-1]
    tf.debugging.assert_all_finite(simulated_returns, "simulated_returns not finite")
    tf.debugging.assert_all_finite(weights, "weights not finite")
    tf.debugging.assert_all_finite(cashflows, "cashflows not finite")
    tf.debugging.assert_all_finite(transactions, "transactions not finite")
    tf.debugging.assert_all_finite(time_steps, "time_steps not finite")

    inflation = tf.cast(inflation, dtype)

    def scan_step(carry, inputs):
        curr_wealth, inflation_factor = carry
        i, ret_t, w_t, cf_t, tr_t, dt = inputs
        growth = tf.reduce_sum(w_t * tf.pow(1.0 + ret_t, dt), axis=-1)
        next_infl = inflation_factor * tf.pow(1.0 + inflation, dt)
        next_wealth = curr_wealth * growth + (cf_t * dt + tr_t) * next_infl
        next_wealth = tf.where(next_wealth < 0, tf.zeros_like(next_wealth), next_wealth)
        return (next_wealth, next_infl), next_wealth

    ret_seq = tf.unstack(simulated_returns, axis=1)
    w_seq = tf.unstack(weights, axis=0)
    cf_seq = tf.unstack(cashflows, axis=0)
    tr_seq = tf.unstack(transactions, axis=0)
    dt_seq = tf.unstack(time_delta, axis=0)

    def to_n(x):
        x = tf.convert_to_tensor(x, dtype)
        return tf.ones((n,), dtype) * x

    inputs = (
        tf.range(s, dtype=tf.int32),
        ret_seq,
        w_seq,
        cf_seq,
        tr_seq,
        dt_seq,
    )
    step_inputs = list(zip(*inputs))

    wealth0 = tf.ones((n,), dtype) * init_w
    infl0 = tf.ones((), dtype)
    carry0 = (wealth0, infl0)

    ta = tf.TensorArray(dtype, size=0, dynamic_size=True, clear_after_read=False)
    carry = carry0
    for i, ret_t, w_t, cf_t, tr_t, dt in step_inputs:
        ret_t = tf.convert_to_tensor(ret_t, dtype)
        w_t = tf.convert_to_tensor(w_t, dtype)
        cf_t = tf.convert_to_tensor(cf_t, dtype)
        tr_t = tf.convert_to_tensor(tr_t, dtype)
        dt = tf.convert_to_tensor(dt, dtype)
        carry, out_w = scan_step(carry, (i, ret_t, w_t, cf_t, tr_t, dt))
        ta = ta.write(ta.size(), out_w)

    wealth_steps = ta.stack()
    wealth_steps = tf.transpose(wealth_steps, perm=[1, 0])
    wealth = tf.concat([tf.expand_dims(wealth0, 1), wealth_steps], axis=1)
    return wealth

