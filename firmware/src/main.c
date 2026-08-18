#include <math.h>
#include <stdio.h>
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/sensor.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>

#define GRAVITY_M_S2 9.80665
#define SAMPLE_INTERVAL_MS 10
#define SETTLING_SECONDS 3
#define CAPTURE_SECONDS 5
#define SAMPLES_PER_CAPTURE (CAPTURE_SECONDS * 1000 / SAMPLE_INTERVAL_MS)

static const struct device *const accelerometer =
    DEVICE_DT_GET(DT_NODELABEL(adxl362));
static const struct gpio_dt_spec button = GPIO_DT_SPEC_GET(DT_ALIAS(sw0), gpios);
static const char *const orientations[] = { "+X", "-X", "+Y", "-Y", "+Z", "-Z" };

static double to_g(const struct sensor_value *value)
{
    return sensor_value_to_double(value) / GRAVITY_M_S2;
}

static void wait_for_button(void)
{
    while (gpio_pin_get_dt(&button) == 0) {
        k_msleep(20);
    }
    k_msleep(40);
    while (gpio_pin_get_dt(&button) != 0) {
        k_msleep(20);
    }
    k_msleep(200);
}

int main(void)
{
    struct sensor_value accel[3];

    printk("# ADXL362 six-position capture\n");

    if (!device_is_ready(accelerometer)) {
        printk("# ERROR: ADXL362 is not ready. Check 3V3, GND, SCLK, MOSI, MISO and CS.\n");
        return 0;
    }
    if (!gpio_is_ready_dt(&button) || gpio_pin_configure_dt(&button, GPIO_INPUT) != 0) {
        printk("# ERROR: DK Button 1 is not ready.\n");
        return 0;
    }

    printk("# Sensor ready. CSV data begins below.\n");
    printk("orientation,time_ms,x,y,z,magnitude\n");

    for (size_t pose = 0; pose < ARRAY_SIZE(orientations); pose++) {
        printk("# Place the board in %s orientation, keep it stable, then press Button 1.\n",
               orientations[pose]);
        wait_for_button();

        for (int seconds = SETTLING_SECONDS; seconds > 0; seconds--) {
            printk("# Settling: %d\n", seconds);
            k_sleep(K_SECONDS(1));
        }

        printk("# Recording %s for %d seconds. Do not touch the board.\n",
               orientations[pose], CAPTURE_SECONDS);

        for (int sample = 0; sample < SAMPLES_PER_CAPTURE; sample++) {
            int rc = sensor_sample_fetch(accelerometer);
            if (rc == 0) {
                rc = sensor_channel_get(accelerometer, SENSOR_CHAN_ACCEL_XYZ, accel);
            }
            if (rc != 0) {
                printk("# ERROR: sensor read failed: %d\n", rc);
                k_msleep(SAMPLE_INTERVAL_MS);
                continue;
            }

            double x = to_g(&accel[0]);
            double y = to_g(&accel[1]);
            double z = to_g(&accel[2]);
            double magnitude = sqrt(x * x + y * y + z * z);

            printk("%s,%lld,%.6f,%.6f,%.6f,%.6f\n",
                   orientations[pose], k_uptime_get(), x, y, z, magnitude);
            k_msleep(SAMPLE_INTERVAL_MS);
        }
        printk("# Completed %s.\n", orientations[pose]);
    }

    printk("# ALL SIX POSITIONS COMPLETE. Save the terminal output as hardware_capture.csv\n");
    while (true) {
        k_sleep(K_SECONDS(1));
    }
    return 0;
}
